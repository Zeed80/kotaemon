import hashlib
import json

import gradio as gr
from sqlmodel import Session, select
from theflow.settings import settings as flowsettings

from ktem.app import BasePage
from ktem.components import reasonings
from ktem.db.models import Settings, User, engine
from ktem.pages.resources.ollama_servers import OllamaServersManagement

KH_SSO_ENABLED = getattr(flowsettings, "KH_SSO_ENABLED", False)

APPLICATION_SETTINGS_PREFIX = "application."


def _persist_application_settings_file(setting: dict) -> None:
    """Записать настройки приложения (application.*) в JSON-файл для учёта при следующем запуске (индексы, флаги).
    Чувствительные поля (api_key и т.п.) шифруются перед записью.
    """
    from ktem.utils.secret_storage import process_dict_for_save

    app_data_dir = getattr(flowsettings, "KH_APP_DATA_DIR", None)
    if not app_data_dir:
        return
    path = app_data_dir / "application_settings.json"
    subset = {}
    for key, value in setting.items():
        if not key.startswith(APPLICATION_SETTINGS_PREFIX):
            continue
        short_key = key[len(APPLICATION_SETTINGS_PREFIX) :]
        if value is None or isinstance(value, (str, int, float, bool)):
            subset[short_key] = value
        elif isinstance(value, (list, dict)):
            try:
                json.dumps(value)
                subset[short_key] = value
            except (TypeError, ValueError):
                pass
    process_dict_for_save(subset, prefix="application.")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(subset, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _sync_application_settings_to_ollama_reranker(setting: dict) -> None:
    """Обновить spec реранкера Ollama в БД из настроек приложения (application.kh_ollama_url, application.ollama_reranker_model)."""
    url = setting.get("application.kh_ollama_url")
    model = setting.get("application.ollama_reranker_model")
    if url is None and model is None:
        return
    from ktem.rerankings.db import RerankingTable
    from ktem.rerankings.manager import reranking_models_manager

    with Session(engine) as session:
        statement = select(RerankingTable).where(RerankingTable.name == "ollama")
        row = session.exec(statement).first()
        if row is None:
            return
        item = row[0] if isinstance(row, (tuple, list)) else row
        spec = dict(item.spec or {})
        if url is not None:
            spec["base_url"] = url
        if model is not None:
            spec["model_name"] = model
        item.spec = spec
        session.add(item)
        session.commit()
    reranking_models_manager.load()


signout_js = """
function(u, c, pw, pwc) {
    removeFromStorage('username');
    removeFromStorage('password');
    return [u, c, pw, pwc];
}
"""


gr_cls_single_value = {
    "text": gr.Textbox,
    "number": gr.Number,
    "checkbox": gr.Checkbox,
}


def _make_password_component(**kwargs):
    """Textbox с маскировкой для паролей и API-ключей."""
    return gr.Textbox(**{**kwargs, "type": "password"})


gr_cls_single_value["password"] = _make_password_component


gr_cls_choices = {
    "dropdown": gr.Dropdown,
    "radio": gr.Radio,
    "checkboxgroup": gr.CheckboxGroup,
}


def _ollama_status_html(ok: bool, message: str) -> str:
    """Вернуть HTML индикатора доступности Ollama (зелёный/серый/красный кружок)."""
    if ok:
        color, title = "#22c55e", "Ollama доступен"
    else:
        color = "#ef4444"
        title = {
            "timeout": "Таймаут",
            "unreachable": "Недоступен",
            "error": "Ошибка",
        }.get(message, "Недоступен")
    return (
        f'<span title="{title}" style="'
        "display: inline-block; width: 14px; height: 14px; border-radius: 50%; "
        f"background: {color}; margin-left: 8px; vertical-align: middle;"
        '" aria-label="Ollama status"></span>'
    )


def render_setting_item(setting_item, value):
    """Render the setting component into corresponding Gradio UI component"""
    kwargs = {
        "label": setting_item.name,
        "value": value,
        "interactive": True,
    }

    if setting_item.component in gr_cls_single_value:
        return gr_cls_single_value[setting_item.component](**kwargs)

    kwargs["choices"] = setting_item.choices

    if setting_item.component in gr_cls_choices:
        return gr_cls_choices[setting_item.component](**kwargs)

    raise ValueError(
        f"Unknown component {setting_item.component}, allowed are: "
        f"{list(gr_cls_single_value.keys()) + list(gr_cls_choices.keys())}.\n"
        f"Setting item: {setting_item}"
    )


class SettingsPage(BasePage):
    """Responsible for allowing the users to customize the application

    **IMPORTANT**: the name and id of the UI setting components should match the
    name of the setting in the `app.default_settings`
    """

    public_events = ["onSignOut"]

    def __init__(self, app):
        """Initiate the page and render the UI"""
        self._app = app

        self._settings_state = app.settings_state
        self._user_id = app.user_id
        self._default_settings = app.default_settings
        self._settings_dict = self._default_settings.flatten()
        self._settings_keys = list(self._settings_dict.keys())

        self._components = {}
        self._reasoning_mode = {}

        # store llms, embeddings and vlms components
        self._llms = []
        self._embeddings = []
        self._vlms = []

        # render application page if there are application settings
        self._render_app_tab = False

        if not KH_SSO_ENABLED and self._default_settings.application.settings:
            self._render_app_tab = True

        # render index page if there are index settings (general and/or specific)
        self._render_index_tab = False

        if not KH_SSO_ENABLED:
            if self._default_settings.index.settings:
                self._render_index_tab = True
            else:
                for sig in self._default_settings.index.options.values():
                    if sig.settings:
                        self._render_index_tab = True
                        break

        # render reasoning page if there are reasoning settings
        self._render_reasoning_tab = False

        if not KH_SSO_ENABLED:
            if len(self._default_settings.reasoning.settings) > 1:
                self._render_reasoning_tab = True
            else:
                for sig in self._default_settings.reasoning.options.values():
                    if sig.settings:
                        self._render_reasoning_tab = True
                        break

        self.on_building_ui()

    def on_building_ui(self):
        if not KH_SSO_ENABLED:
            self.setting_save_btn = gr.Button(
                "Save & Close",
                variant="primary",
                elem_classes=["right-button"],
                elem_id="save-setting-btn",
            )
        if self._app.f_user_management:
            with gr.Tab("User settings"):
                self.user_tab()

        with gr.Tab("Ollama servers"):
            self.ollama_servers_management = OllamaServersManagement(self._app)

        self.app_tab()
        self.index_tab()
        self.reasoning_tab()

    def on_subscribe_public_events(self):
        """
        Subscribes to public events related to user management.

        This function is responsible for subscribing to the "onSignIn" event, which is
        triggered when a user signs in. It registers two event handlers for this event.

        The first event handler, "load_setting", is responsible for loading the user's
        settings when they sign in. It takes the user ID as input and returns the
        settings state and a list of component outputs. The progress indicator for this
        event is set to "hidden".

        The second event handler, "get_name", is responsible for retrieving the
        username of the current user. It takes the user ID as input and returns the
        username if it exists, otherwise it returns "___". The progress indicator for
        this event is also set to "hidden".

        Parameters:
            self (object): The instance of the class.

        Returns:
            None
        """
        if self._app.f_user_management:
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.load_setting,
                    "inputs": self._user_id,
                    "outputs": [self._settings_state] + self.components(),
                    "show_progress": "hidden",
                },
            )

            def get_name(user_id):
                name = "Current user: "
                if user_id:
                    with Session(engine) as session:
                        statement = select(User).where(User.id == user_id)
                        result = session.exec(statement).all()
                        if result:
                            return name + result[0].username
                return name + "___"

            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": get_name,
                    "inputs": self._user_id,
                    "outputs": [self.current_name],
                    "show_progress": "hidden",
                },
            )

    def on_register_events(self):
        if not KH_SSO_ENABLED:
            self.setting_save_btn.click(
                self.save_setting,
                inputs=[self._user_id] + self.components(),
                outputs=self._settings_state,
            ).then(
                lambda: gr.Tabs(selected="chat-tab"),
                outputs=self._app.tabs,
            )
        self._components["reasoning.use"].change(
            self.change_reasoning_mode,
            inputs=[self._components["reasoning.use"]],
            outputs=list(self._reasoning_mode.values()),
            show_progress="hidden",
        )
        if self._app.f_user_management and not KH_SSO_ENABLED:
            self.password_change_btn.click(
                self.change_password,
                inputs=[
                    self._user_id,
                    self.password_change,
                    self.password_change_confirm,
                ],
                outputs=[self.password_change, self.password_change_confirm],
                show_progress="hidden",
            )
            onSignOutClick = self.signout.click(
                lambda: (None, "Current user: ___", "", ""),
                inputs=[],
                outputs=[
                    self._user_id,
                    self.current_name,
                    self.password_change,
                    self.password_change_confirm,
                ],
                show_progress="hidden",
                js=signout_js,
            ).then(
                self.load_setting,
                inputs=self._user_id,
                outputs=[self._settings_state] + self.components(),
                show_progress="hidden",
            )
            for event in self._app.get_event("onSignOut"):
                onSignOutClick = onSignOutClick.then(**event)

    def user_tab(self):
        # user management
        self.current_name = gr.Markdown("Current user: ___")

        if KH_SSO_ENABLED:
            import gradiologin as grlogin

            self.sso_signout = grlogin.LogoutButton("Logout")
        else:
            self.signout = gr.Button("Logout")

            self.password_change = gr.Textbox(
                label="New password", interactive=True, type="password"
            )
            self.password_change_confirm = gr.Textbox(
                label="Confirm password", interactive=True, type="password"
            )
            self.password_change_btn = gr.Button("Change password", interactive=True)

    def change_password(self, user_id, password, password_confirm):
        from ktem.pages.resources.user import validate_password

        errors = validate_password(password, password_confirm)
        if errors:
            print(errors)
            gr.Warning(errors)
            return password, password_confirm

        with Session(engine) as session:
            statement = select(User).where(User.id == user_id)
            result = session.exec(statement).all()
            if result:
                user = result[0]
                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                user.password = hashed_password
                session.add(user)
                session.commit()
                gr.Info("Password changed")
            else:
                gr.Warning("User not found")

        return "", ""

    def app_tab(self):
        with gr.Tab("General", visible=self._render_app_tab):
            for n, si in self._default_settings.application.settings.items():
                if n == "kh_ollama_url":
                    # Пропускаем поле kh_ollama_url - управление серверами Ollama теперь в отдельной вкладке
                    continue
                obj = render_setting_item(si, si.value)
                self._components[f"application.{n}"] = obj
                if si.special_type == "llm":
                    self._llms.append(obj)
                if si.special_type == "embedding":
                    self._embeddings.append(obj)
            gr.Markdown(
                "*Изменение флагов индексов (LightRAG, Nano GraphRAG), "
                "настроек Qdrant и т.д. вступает в силу после перезапуска приложения.*"
            )

    def index_tab(self):
        # TODO: double check if we need general
        # with gr.Tab("General"):
        #     for n, si in self._default_settings.index.settings.items():
        #         obj = render_setting_item(si, si.value)
        #         self._components[f"index.{n}"] = obj

        id2name = {k: v.name for k, v in self._app.index_manager.info().items()}
        with gr.Tab("Retrieval settings", visible=self._render_index_tab):
            gr.Markdown(
                "Document recognition modes:\n"
                "- `ocr`: classic OCR/readers (stable fallback)\n"
                "- `vlm`: multimodal extraction (requires a working VLM endpoint/model)\n\n"
                "For Ollama VLM, make sure server and model are available before indexing."
            )
            for pn, sig in self._default_settings.index.options.items():
                name = id2name.get(pn, f"<id {pn}>")
                with gr.Tab(name):
                    for n, si in sig.settings.items():
                        obj = render_setting_item(si, si.value)
                        self._components[f"index.options.{pn}.{n}"] = obj
                        if si.special_type == "llm":
                            self._llms.append(obj)
                        if si.special_type == "embedding":
                            self._embeddings.append(obj)
                        if si.special_type == "vlm":
                            self._vlms.append(obj)

    def reasoning_tab(self):
        with gr.Tab("Reasoning settings", visible=self._render_reasoning_tab):
            with gr.Group():
                for n, si in self._default_settings.reasoning.settings.items():
                    if n == "use":
                        continue
                    obj = render_setting_item(si, si.value)
                    self._components[f"reasoning.{n}"] = obj
                    if si.special_type == "llm":
                        self._llms.append(obj)
                    if si.special_type == "embedding":
                        self._embeddings.append(obj)

            gr.Markdown("### Reasoning-specific settings")
            self._components["reasoning.use"] = render_setting_item(
                self._default_settings.reasoning.settings["use"],
                self._default_settings.reasoning.settings["use"].value,
            )

            for idx, (pn, sig) in enumerate(
                self._default_settings.reasoning.options.items()
            ):
                with gr.Group(
                    visible=idx == 0,
                    elem_id=pn,
                ) as self._reasoning_mode[pn]:
                    reasoning = reasonings.get(pn, None)
                    if reasoning is None:
                        gr.Markdown("**Name**: Description")
                    else:
                        info = reasoning.get_info()
                        gr.Markdown(f"**{info['name']}**: {info['description']}")
                    for n, si in sig.settings.items():
                        obj = render_setting_item(si, si.value)
                        self._components[f"reasoning.options.{pn}.{n}"] = obj
                        if si.special_type == "llm":
                            self._llms.append(obj)
                        if si.special_type == "embedding":
                            self._embeddings.append(obj)

    def change_reasoning_mode(self, value):
        output = []
        for each in self._reasoning_mode.values():
            if value == each.elem_id:
                output.append(gr.update(visible=True))
            else:
                output.append(gr.update(visible=False))
        return output

    def load_setting(self, user_id=None):
        from ktem.utils.secret_storage import process_dict_for_load

        settings = self._settings_dict.copy()  # Копируем дефолтные настройки
        try:
            with Session(engine) as session:
                statement = select(Settings).where(Settings.user == user_id)
                result = session.exec(statement).all()
                if result:
                    # Обновляем только те настройки, которые есть в БД
                    db_settings = result[0].setting
                    if db_settings:
                        settings.update(db_settings)
            process_dict_for_load(settings)
        except Exception as e:
            gr.Warning(f"Failed to load settings: {e}")

        output = [settings]
        # Безопасное получение настроек с дефолтными значениями
        output += tuple(
            settings.get(name, self._settings_dict.get(name))
            for name in self.component_names()
        )
        return output

    def save_setting(self, user_id: int, *args):
        """Save the setting to disk and persist the setting to session state

        Args:
            user_id: the user id
            args: all the values from the settings
        """
        setting = {
            key: value for key, value in zip(self.component_names(), args, strict=False)
        }
        if user_id is None:
            gr.Warning("Need to login before saving settings")
            return setting

        from ktem.utils.secret_storage import process_dict_for_save

        process_dict_for_save(setting)

        try:
            with Session(engine) as session:
                statement = select(Settings).where(Settings.user == user_id)
                try:
                    user_setting = session.exec(statement).one()
                except Exception:
                    user_setting = Settings()
                    user_setting.user = user_id
                user_setting.setting = setting
                session.add(user_setting)
                session.commit()

            _sync_application_settings_to_ollama_reranker(setting)
            _persist_application_settings_file(setting)

            gr.Info("Setting saved")
        except Exception as e:
            gr.Warning(f"Failed to save settings: {e}")
        return setting

    def components(self) -> list:
        """Get the setting components"""
        output = []
        for name in self._settings_keys:
            if name not in self._components:
                continue  # Пропускаем поля, которые не рендерятся (например kh_ollama_url)
            output.append(self._components[name])
        return output

    def component_names(self):
        """Get the setting components"""
        # Исключаем kh_ollama_url, так как управление серверами Ollama теперь в отдельной вкладке
        return [
            name for name in self._settings_keys if name != "application.kh_ollama_url"
        ]

    def _on_app_created(self):
        if not self._app.f_user_management:
            self._app.app.load(
                self.load_setting,
                inputs=self._user_id,
                outputs=[self._settings_state] + self.components(),
                show_progress="hidden",
            )

        def update_llms():
            from ktem.llms.manager import llms

            if llms._default:
                llm_choices = [(f"{llms._default} (default)", "")]
            else:
                llm_choices = [("(random)", "")]
            llm_choices += [(_, _) for _ in llms.options().keys()]
            return gr.update(choices=llm_choices)

        def update_embeddings():
            from ktem.embeddings.manager import embedding_models_manager

            if embedding_models_manager._default:
                emb_choices = [(f"{embedding_models_manager._default} (default)", "")]
            else:
                emb_choices = [("(random)", "")]
            emb_choices += [(_, _) for _ in embedding_models_manager.options().keys()]
            return gr.update(choices=emb_choices)

        def update_vlms():
            from theflow.settings import settings as flowsettings

            vlm_choices = [("Default (from env)", "default")]
            try:
                from ktem.vlms import vlms_manager

                vlm_choices += vlms_manager.options_for_dropdown()
            except Exception:
                vlm_choices += getattr(
                    flowsettings, "KH_VLM_OPTIONS", [("Default", "default")]
                )[1:]
            return gr.update(choices=vlm_choices)

        for llm in self._llms:
            self._app.app.load(
                update_llms,
                inputs=[],
                outputs=[llm],
                show_progress="hidden",
            )
        for emb in self._embeddings:
            self._app.app.load(
                update_embeddings,
                inputs=[],
                outputs=[emb],
                show_progress="hidden",
            )
        for vlm in self._vlms:
            self._app.app.load(
                update_vlms,
                inputs=[],
                outputs=[vlm],
                show_progress="hidden",
            )
