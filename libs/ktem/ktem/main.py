# Применяем патч для httplib2/pyparsing совместимости ДО импорта других модулей
from ktem.utils.httplib2_patch import patch_httplib2_pyparsing  # noqa

patch_httplib2_pyparsing()

import gradio as gr
from theflow.settings import settings as flowsettings

from flowsettings_config import config
from ktem.app import BaseApp
from ktem.i18n import SUPPORTED_UI_LANGS, get_text
from ktem.pages.chat import ChatPage
from ktem.pages.help import HelpPage
from ktem.pages.resources import ResourcesTab
from ktem.pages.settings import SettingsPage
from ktem.pages.setup import SetupPage
from ktem.pages.upload import UnifiedUploadPage

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
KH_SSO_ENABLED = getattr(flowsettings, "KH_SSO_ENABLED", False)
KH_ENABLE_FIRST_SETUP = getattr(flowsettings, "KH_ENABLE_FIRST_SETUP", False)
KH_APP_DATA_EXISTS = getattr(flowsettings, "KH_APP_DATA_EXISTS", True)

# override first setup setting
if config("KH_FIRST_SETUP", default=False, cast=bool):
    KH_APP_DATA_EXISTS = False


def toggle_first_setup_visibility():
    global KH_APP_DATA_EXISTS
    is_first_setup = not KH_DEMO_MODE and not KH_APP_DATA_EXISTS
    KH_APP_DATA_EXISTS = True
    return gr.update(visible=is_first_setup), gr.update(visible=not is_first_setup)


class App(BaseApp):
    """The main app of Kotaemon

    The main application contains app-level information:
        - setting state
        - user id

    App life-cycle:
        - Render
        - Declare public events
        - Subscribe public events
        - Register events
    """

    def ui(self):
        """Render the UI"""
        self._tabs = {}

        def t(key):
            return get_text("en", key)

        with gr.Tabs() as self.tabs:
            if self.f_user_management:
                from ktem.pages.login import LoginPage

                with gr.Tab(
                    t("tab.welcome"), elem_id="login-tab", id="login-tab"
                ) as self._tabs["login-tab"]:
                    self.login_page = LoginPage(self)

            with gr.Tab(
                t("tab.chat"),
                elem_id="chat-tab",
                id="chat-tab",
                visible=not self.f_user_management,
            ) as self._tabs["chat-tab"]:
                self.chat_page = ChatPage(self)

            if len(self.index_manager.indices) == 1:
                for index in self.index_manager.indices:
                    with gr.Tab(
                        f"{index.name}",
                        elem_id="indices-tab",
                        elem_classes=[
                            "fill-main-area-height",
                            "scrollable",
                            "indices-tab",
                        ],
                        id="indices-tab",
                        visible=not self.f_user_management and not KH_DEMO_MODE,
                    ) as self._tabs[f"{index.id}-tab"]:
                        page = index.get_index_page_ui()
                        setattr(self, f"_index_{index.id}", page)
            elif len(self.index_manager.indices) > 1:
                with gr.Tab(
                    t("tab.files"),
                    elem_id="indices-tab",
                    elem_classes=["fill-main-area-height", "scrollable", "indices-tab"],
                    id="indices-tab",
                    visible=not self.f_user_management and not KH_DEMO_MODE,
                ) as self._tabs["indices-tab"]:
                    for index in self.index_manager.indices:
                        with gr.Tab(
                            index.name,
                            elem_id=f"{index.id}-tab",
                        ) as self._tabs[f"{index.id}-tab"]:
                            page = index.get_index_page_ui()
                            setattr(self, f"_index_{index.id}", page)

            if not KH_DEMO_MODE and config(
                "ENABLE_UNIFIED_UPLOAD", default=True, cast=bool
            ):
                with gr.Tab(
                    "Upload",
                    elem_id="upload-tab",
                    elem_classes=["fill-main-area-height", "scrollable"],
                    id="upload-tab",
                    visible=not self.f_user_management,
                ) as self._tabs["upload-tab"]:
                    self.upload_page = UnifiedUploadPage(self)

            if not KH_DEMO_MODE:
                if not KH_SSO_ENABLED:
                    with gr.Tab(
                        t("tab.resources"),
                        elem_id="resources-tab",
                        id="resources-tab",
                        visible=not self.f_user_management,
                        elem_classes=["fill-main-area-height", "scrollable"],
                    ) as self._tabs["resources-tab"]:
                        self.resources_page = ResourcesTab(self)

                with gr.Tab(
                    t("tab.settings"),
                    elem_id="settings-tab",
                    id="settings-tab",
                    visible=not self.f_user_management,
                    elem_classes=["fill-main-area-height", "scrollable"],
                ) as self._tabs["settings-tab"]:
                    self.settings_page = SettingsPage(self)

            with gr.Tab(
                t("tab.help"),
                elem_id="help-tab",
                id="help-tab",
                visible=not self.f_user_management,
                elem_classes=["fill-main-area-height", "scrollable"],
            ) as self._tabs["help-tab"]:
                self.help_page = HelpPage(self)

        if KH_ENABLE_FIRST_SETUP:
            with gr.Column(visible=False) as self.setup_page_wrapper:
                self.setup_page = SetupPage(self)

    def on_subscribe_public_events(self):
        if self.f_user_management:
            from sqlmodel import Session, select

            from ktem.db.engine import engine
            from ktem.db.models import User

            def toggle_login_visibility(user_id):
                if not user_id:
                    return list(
                        (
                            gr.update(visible=True)
                            if k == "login-tab"
                            else gr.update(visible=False)
                        )
                        for k in self._tabs.keys()
                    ) + [gr.update(selected="login-tab")]

                with Session(engine) as session:
                    user = session.exec(select(User).where(User.id == user_id)).first()
                    if user is None:
                        return list(
                            (
                                gr.update(visible=True)
                                if k == "login-tab"
                                else gr.update(visible=False)
                            )
                            for k in self._tabs.keys()
                        )

                    is_admin = user.admin

                tabs_update = []
                for k in self._tabs.keys():
                    if k == "login-tab":
                        tabs_update.append(gr.update(visible=False))
                    elif k == "resources-tab":
                        tabs_update.append(gr.update(visible=is_admin))
                    else:
                        tabs_update.append(gr.update(visible=True))

                tabs_update.append(gr.update(selected="chat-tab"))

                return tabs_update

            self.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": toggle_login_visibility,
                    "inputs": [self.user_id],
                    "outputs": list(self._tabs.values()) + [self.tabs],
                    "show_progress": "hidden",
                },
            )

            self.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": toggle_login_visibility,
                    "inputs": [self.user_id],
                    "outputs": list(self._tabs.values()) + [self.tabs],
                    "show_progress": "hidden",
                },
            )

        if KH_ENABLE_FIRST_SETUP:
            self.subscribe_event(
                name="onFirstSetupComplete",
                definition={
                    "fn": toggle_first_setup_visibility,
                    "inputs": [],
                    "outputs": [self.setup_page_wrapper, self.tabs],
                    "show_progress": "hidden",
                },
            )

    def on_register_events(self):
        super().on_register_events()

        outputs = []
        keys = []
        if "login-tab" in self._tabs:
            outputs.append(self._tabs["login-tab"])
            keys.append("tab.welcome")
        outputs.append(self._tabs["chat-tab"])
        keys.append("tab.chat")
        if "indices-tab" in self._tabs:
            outputs.append(self._tabs["indices-tab"])
            keys.append("tab.files")
        if "resources-tab" in self._tabs:
            outputs.append(self._tabs["resources-tab"])
            keys.append("tab.resources")
        outputs.append(self._tabs["settings-tab"])
        keys.append("tab.settings")
        outputs.append(self._tabs["help-tab"])
        keys.append("tab.help")
        outputs.append(self.version_html)

        if (
            outputs
            and hasattr(self, "lang_dropdown")
            and self.lang_dropdown is not None
        ):

            def on_lang_change(lang):
                tab_updates = [gr.update(label=get_text(lang, k)) for k in keys]
                version_update = gr.update(
                    value=f'<p id="version-display" class="version-text">'
                    f'{get_text(lang, "version")}: {self.app_version}</p>'
                )
                return tab_updates + [version_update]

            def save_ui_lang(lang):
                """Сохранить язык интерфейса в state и localStorage."""
                if lang and lang in [code for _, code in SUPPORTED_UI_LANGS]:
                    # Сохраняем в state для использования в сессии
                    return lang
                return "en"

            self.lang_dropdown.change(
                fn=on_lang_change,
                inputs=[self.lang_dropdown],
                outputs=outputs,
                show_progress="hidden",
            )
            self.lang_dropdown.change(
                fn=save_ui_lang,
                inputs=[self.lang_dropdown],
                outputs=[self.ui_lang],
                show_progress="hidden",
            )
            self.lang_dropdown.change(
                fn=None,
                inputs=[self.lang_dropdown],
                outputs=[],
                js="(lang) => { if (window.applyUiLang) window.applyUiLang(lang); if (window.setStorage) window.setStorage('ui_lang', lang); document.cookie = 'ui_lang=' + encodeURIComponent(lang) + '; path=/; max-age=31536000'; }",
            )

    def _on_app_created(self):
        """Called when the app is created"""
        if config("ENABLE_BACKGROUND_INDEXING", default=True, cast=bool):
            try:
                from ktem.orchestration.queue import get_indexing_queue

                get_indexing_queue(self)
            except Exception:
                pass

        if KH_ENABLE_FIRST_SETUP:
            self.app.load(
                toggle_first_setup_visibility,
                inputs=[],
                outputs=[self.setup_page_wrapper, self.tabs],
            )

        # Загрузить сохранённый язык при старте: читаем из cookie (сервер) и обновляем вкладки/версию
        load_lang_keys = []
        load_lang_outputs = []
        if "login-tab" in self._tabs:
            load_lang_outputs.append(self._tabs["login-tab"])
            load_lang_keys.append("tab.welcome")
        load_lang_outputs.append(self._tabs["chat-tab"])
        load_lang_keys.append("tab.chat")
        if "indices-tab" in self._tabs:
            load_lang_outputs.append(self._tabs["indices-tab"])
            load_lang_keys.append("tab.files")
        if "resources-tab" in self._tabs:
            load_lang_outputs.append(self._tabs["resources-tab"])
            load_lang_keys.append("tab.resources")
        load_lang_outputs.append(self._tabs["settings-tab"])
        load_lang_keys.append("tab.settings")
        load_lang_outputs.append(self._tabs["help-tab"])
        load_lang_keys.append("tab.help")
        load_lang_outputs.append(self.version_html)

        def load_saved_lang():
            """Возвращает дефолт (en); сохранённый язык подставляется на клиенте через JS."""
            saved = "en"
            valid_codes = [code for _, code in SUPPORTED_UI_LANGS]
            if saved not in valid_codes:
                saved = "en"
            tab_updates = [gr.update(label=get_text(saved, k)) for k in load_lang_keys]
            version_update = gr.update(
                value=f'<p id="version-display" class="version-text">'
                f'{get_text(saved, "version")}: {self.app_version}</p>'
            )
            return [saved, saved] + tab_updates + [version_update]

        if (
            load_lang_outputs
            and hasattr(self, "lang_dropdown")
            and self.lang_dropdown is not None
        ):
            self.app.load(
                fn=load_saved_lang,
                inputs=[],
                outputs=[self.lang_dropdown, self.ui_lang] + load_lang_outputs,
                show_progress="hidden",
                js="""
                () => {
                    var saved = localStorage.getItem('ui_lang') || 'en';
                    setTimeout(function() {
                        var el = document.querySelector('#lang-dropdown');
                        if (el) {
                            var sel = el.querySelector('select');
                            var inp = el.querySelector('input');
                            if (sel && sel.value !== saved) {
                                sel.value = saved;
                                sel.dispatchEvent(new Event('change', { bubbles: true }));
                            } else if (inp && inp.value !== saved) {
                                inp.value = saved;
                                inp.dispatchEvent(new Event('input', { bubbles: true }));
                                inp.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                        if (window.applyUiLang) window.applyUiLang(saved);
                    }, 300);
                }
                """,
            )
