from copy import deepcopy
from typing import cast

import gradio as gr
import pandas as pd
import yaml
from theflow.utils.modules import deserialize

from ktem.app import BasePage
from ktem.ollama_servers import ollama_servers_manager
from ktem.utils.file import YAMLNoDateSafeLoader
from ktem.utils.ollama import get_ollama_base_url, get_ollama_models, pull_ollama_model

from .manager import embedding_models_manager


def format_description(cls):
    params = cls.describe()["params"]
    params_lines = ["| Name | Type | Description |", "| --- | --- | --- |"]
    for key, value in params.items():
        if isinstance(value["auto_callback"], str):
            continue
        params_lines.append(f"| {key} | {value['type']} | {value['help']} |")
    return f"{cls.__doc__}\n\n" + "\n".join(params_lines)


class EmbeddingManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.spec_desc_default = (
            "# Spec description\n\nSelect a model to view the spec description."
        )
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.emb_list = gr.DataFrame(
                headers=["name", "vendor", "default"],
                interactive=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_emb_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_default = gr.Checkbox(
                            label="Set default",
                            info=(
                                "Set this Embedding model as default. This default "
                                "Embedding will be used by other components by default "
                                "if no Embedding is specified for such components."
                            ),
                        )
                        with gr.Row(visible=False) as self._edit_ollama_row:
                            self.edit_ollama_server = gr.Dropdown(
                                label="Ollama server",
                                choices=[],
                                value=None,
                                allow_custom_value=False,
                            )
                            self.edit_ollama_model = gr.Dropdown(
                                label="Ollama model",
                                info="Смена модели обновит спецификацию ниже",
                                choices=[],
                                value=None,
                                allow_custom_value=True,
                                interactive=True,
                            )
                        self.edit_spec = gr.Textbox(
                            label="Specification",
                            info="Specification of the Embedding model in YAML format",
                            lines=10,
                        )

                        with gr.Accordion(
                            label="Test connection", visible=False, open=False
                        ) as self._check_connection_panel:
                            with gr.Row():
                                with gr.Column(scale=4):
                                    self.connection_logs = gr.HTML(
                                        "Logs",
                                    )

                                with gr.Column(scale=1):
                                    self.btn_test_connection = gr.Button("Test")

                        with gr.Row(visible=False) as self._selected_panel_btn:
                            with gr.Column():
                                self.btn_edit_save = gr.Button(
                                    "Save", min_width=10, variant="primary"
                                )
                            with gr.Column():
                                self.btn_delete = gr.Button(
                                    "Delete", min_width=10, variant="stop"
                                )
                                with gr.Row():
                                    self.btn_delete_yes = gr.Button(
                                        "Confirm Delete",
                                        variant="stop",
                                        visible=False,
                                        min_width=10,
                                    )
                                    self.btn_delete_no = gr.Button(
                                        "Cancel", visible=False, min_width=10
                                    )
                            with gr.Column():
                                self.btn_close = gr.Button("Close", min_width=10)

                    with gr.Column():
                        self.edit_spec_desc = gr.Markdown("# Spec description")

        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="Name",
                        info=(
                            "Must be unique and non-empty. "
                            "The name will be used to identify the embedding model."
                        ),
                    )
                    self.emb_choices = gr.Dropdown(
                        label="Vendors",
                        info=(
                            "Choose the vendor of the Embedding model. Each vendor "
                            "has different specification."
                        ),
                    )
                    self.spec = gr.Textbox(
                        label="Specification",
                        info="Specification of the Embedding model in YAML format.",
                    )
                    self.default = gr.Checkbox(
                        label="Set default",
                        info=(
                            "Set this Embedding model as default. This default "
                            "Embedding will be used by other components by default "
                            "if no Embedding is specified for such components."
                        ),
                    )
                    self.btn_new = gr.Button("Add", variant="primary")

                    # Ollama-specific UI elements for OpenAIEmbeddings
                    with gr.Column(visible=False) as self.ollama_section:
                        gr.Markdown("### Ollama")
                        self.ollama_server_dropdown = gr.Dropdown(
                            label="Ollama server",
                            choices=[],
                            value=None,
                            info="Choose a registered Ollama server (Settings → Ollama servers)",
                        )
                        gr.Markdown("### Model")
                        with gr.Row():
                            self.ollama_model_dropdown = gr.Dropdown(
                                label="Available Ollama models",
                                info="Select a model from your Ollama installation",
                                choices=[],
                                value=None,
                                allow_custom_value=True,
                                interactive=True,
                            )
                            self.btn_refresh_ollama_models = gr.Button(
                                "🔄 Refresh", scale=0, min_width=100
                            )
                        self.ollama_model_input = gr.Textbox(
                            label="Or enter model name manually",
                            info="Enter model name if not in the list above",
                            placeholder="e.g., nomic-embed-text",
                        )
                        with gr.Row():
                            self.btn_pull_ollama_model = gr.Button(
                                "⬇️ Pull Model", variant="secondary"
                            )
                            self.ollama_pull_progress = gr.HTML(visible=False, value="")

                with gr.Column(scale=3):
                    self.spec_desc = gr.Markdown(self.spec_desc_default)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_embeddings,
            inputs=[],
            outputs=[self.emb_list],
        )
        self._app.app.load(
            lambda: gr.update(choices=list(embedding_models_manager.vendors().keys())),
            outputs=[self.emb_choices],
        )

        def _ollama_server_choices() -> list[str]:
            opts = cast(
                list[tuple[str, str]],
                ollama_servers_manager.options_for_dropdown() or [],
            )
            return [c[1] for c in opts]

        self._app.app.load(
            lambda: gr.update(choices=_ollama_server_choices()),
            outputs=[self.ollama_server_dropdown],
        )
        self._app.app.load(
            self._refresh_ollama_models_for_embeddings,
            inputs=[self.ollama_server_dropdown],
            outputs=[self.ollama_model_dropdown],
        )
        self._app.app.load(
            lambda: gr.update(choices=_ollama_server_choices()),
            inputs=[],
            outputs=[self.edit_ollama_server],
        )

    def on_emb_vendor_change(self, vendor):
        vendor_cls = embedding_models_manager.vendors()[vendor]
        vendor_name = vendor_cls.__name__

        required: dict = {}
        desc = vendor_cls.describe()
        for key, value in desc["params"].items():
            if value.get("required", False):
                required[key] = value.get("default", None)

        # Ollama: LCOllamaEmbeddings или OpenAIEmbeddings (с base_url для Ollama)
        is_ollama_compatible = vendor_name in ("LCOllamaEmbeddings", "OpenAIEmbeddings")

        # Auto-fill base_url for Ollama if OpenAIEmbeddings
        if is_ollama_compatible:
            # Предлагаем Ollama URL как опцию, но не заполняем автоматически
            # Пользователь может выбрать использовать Ollama или OpenAI
            pass

        spec_yaml = yaml.dump(required)
        desc_markdown = format_description(vendor_cls)

        opts = cast(
            list[tuple[str, str]],
            ollama_servers_manager.options_for_dropdown() or [],
        )
        server_choices = [c[1] for c in opts]
        server_value = server_choices[0] if server_choices else None

        return (
            spec_yaml,
            desc_markdown,
            gr.update(visible=is_ollama_compatible),
            gr.update(choices=server_choices, value=server_value),
            gr.update(value=""),
            gr.update(value=""),
        )

    def _refresh_ollama_models_for_embeddings(self, server_name=None):
        """Refresh Ollama embedding models, optionally from specific server."""
        base_url = None
        if server_name:
            s = ollama_servers_manager.get(server_name)
            if s:
                base_url = s["base_url"]
        try:
            models = get_ollama_models(base_url)
            choices = [m["name"] for m in models] if models else []
            return gr.update(choices=choices, value=choices[0] if choices else None)
        except Exception as e:
            gr.Warning(f"Не удалось получить модели Ollama: {e}", duration=1)
            return gr.update(choices=[], value=None)

    def on_register_events(self):
        self.emb_choices.select(
            self.on_emb_vendor_change,
            inputs=[self.emb_choices],
            outputs=[
                self.spec,
                self.spec_desc,
                self.ollama_section,
                self.ollama_server_dropdown,
                self.ollama_model_dropdown,
                self.ollama_model_input,
            ],
        )
        self.ollama_server_dropdown.change(
            self._refresh_ollama_models_for_embeddings,
            inputs=[self.ollama_server_dropdown],
            outputs=[self.ollama_model_dropdown],
        )
        self.btn_refresh_ollama_models.click(
            self._refresh_ollama_models_for_embeddings,
            inputs=[self.ollama_server_dropdown],
            outputs=[self.ollama_model_dropdown],
        )
        self.ollama_model_dropdown.change(
            self.on_ollama_model_selected,
            inputs=[self.ollama_model_dropdown, self.spec],
            outputs=[self.spec],
        )
        self.btn_pull_ollama_model.click(
            self.pull_ollama_model_ui,
            inputs=[
                self.ollama_server_dropdown,
                self.ollama_model_dropdown,
                self.ollama_model_input,
            ],
            outputs=[self.ollama_pull_progress, self.ollama_model_dropdown],
            show_progress="minimal",
        )
        self.btn_new.click(
            self.create_emb,
            inputs=[
                self.name,
                self.emb_choices,
                self.spec,
                self.default,
                self.ollama_server_dropdown,
                self.ollama_model_dropdown,
                self.ollama_model_input,
            ],
            outputs=None,
        ).success(self.list_embeddings, inputs=[], outputs=[self.emb_list]).success(
            lambda: (
                "",
                None,
                "",
                False,
                self.spec_desc_default,
                None,
                "",
                "",
            ),
            outputs=[
                self.name,
                self.emb_choices,
                self.spec,
                self.default,
                self.spec_desc,
                self.ollama_server_dropdown,
                self.ollama_model_dropdown,
                self.ollama_model_input,
            ],
        )
        self.emb_list.select(
            self.select_emb,
            inputs=self.emb_list,
            outputs=[self.selected_emb_name],
            show_progress="hidden",
        )
        self.selected_emb_name.change(
            self.on_selected_emb_change,
            inputs=[self.selected_emb_name],
            outputs=[
                self._selected_panel,
                self._selected_panel_btn,
                # delete section
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no,
                # edit section
                self.edit_spec,
                self.edit_spec_desc,
                self.edit_default,
                self._check_connection_panel,
                # Ollama edit row (visible only for Ollama embeddings)
                self._edit_ollama_row,
                self.edit_ollama_server,
                self.edit_ollama_model,
            ],
            show_progress="hidden",
        ).success(lambda: gr.update(value=""), outputs=[self.connection_logs])

        self.edit_ollama_model.change(
            self._on_edit_ollama_model_change,
            inputs=[self.edit_ollama_model, self.edit_spec],
            outputs=[self.edit_spec],
            show_progress="hidden",
        )
        self.edit_ollama_server.change(
            self._refresh_edit_ollama_models,
            inputs=[self.edit_ollama_server],
            outputs=[self.edit_ollama_model],
            show_progress="hidden",
        )

        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_emb,
            inputs=[self.selected_emb_name],
            outputs=[self.selected_emb_name],
            show_progress="hidden",
        ).then(
            self.list_embeddings,
            inputs=[],
            outputs=[self.emb_list],
        )
        self.btn_delete_no.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ),
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_edit_save.click(
            self.save_emb,
            inputs=[
                self.selected_emb_name,
                self.edit_default,
                self.edit_spec,
            ],
            show_progress="hidden",
        ).then(
            self.list_embeddings,
            inputs=[],
            outputs=[self.emb_list],
        )
        self.btn_close.click(
            lambda: "",
            outputs=[self.selected_emb_name],
        )

        self.btn_test_connection.click(
            self.check_connection,
            inputs=[self.selected_emb_name, self.edit_spec],
            outputs=[self.connection_logs],
        )

    def create_emb(
        self,
        name,
        choices,
        spec,
        default,
        ollama_server=None,
        ollama_model_dropdown=None,
        ollama_model_input=None,
    ):
        try:
            vendor_cls = embedding_models_manager.vendors().get(choices)
            if not vendor_cls:
                raise gr.Error("Выберите провайдера")
            type_str = vendor_cls.__module__ + "." + vendor_cls.__qualname__
            vendor_name = vendor_cls.__name__

            if vendor_name == "LCOllamaEmbeddings":
                model = (ollama_model_dropdown or "").strip() or (
                    ollama_model_input or ""
                ).strip()
                if model and ollama_server:
                    s = ollama_servers_manager.get(ollama_server)
                    if s:
                        base = (
                            s["base_url"]
                            .rstrip("/")
                            .replace("/api", "")
                            .replace("/v1", "")
                        )
                        base_url = f"{base}" if base else "http://localhost:11434"
                        spec = {
                            "__type__": type_str,
                            "base_url": base_url,
                            "model": model,
                        }
                    else:
                        spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
                        spec["__type__"] = type_str
                else:
                    spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
                    spec["__type__"] = type_str
            elif vendor_name == "OpenAIEmbeddings":
                model = (ollama_model_dropdown or "").strip() or (
                    ollama_model_input or ""
                ).strip()
                if model:
                    base_url = get_ollama_base_url().replace("/api", "/v1/")
                    if ollama_server:
                        s = ollama_servers_manager.get(ollama_server)
                        if s:
                            base = (
                                s["base_url"]
                                .rstrip("/")
                                .replace("/api", "")
                                .replace("/v1", "")
                            )
                            base_url = f"{base}/v1/" if base else base_url
                    spec = {
                        "__type__": type_str,
                        "model": model,
                        "base_url": base_url,
                        "api_key": "ollama",
                    }
                else:
                    spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
                    spec["__type__"] = type_str
            else:
                spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
                spec["__type__"] = type_str

            embedding_models_manager.add(name, spec=spec, default=default)
            gr.Info(f'Create Embedding model "{name}" successfully', duration=1)
        except gr.Error:
            raise
        except Exception as e:
            raise gr.Error(f"Failed to create Embedding model {name}: {e}")

    def list_embeddings(self):
        """List the Embedding models (including those that failed to load)."""
        info = embedding_models_manager.info()
        items = []
        for name, spec, default in embedding_models_manager.list_all_from_db():
            record = {"name": name, "default": default}
            if name in info:
                record["vendor"] = (
                    info[name]["spec"].get("__type__", "-").split(".")[-1]
                )
            else:
                record["vendor"] = (
                    spec.get("__type__", "-").split(".")[-1] + " (загрузка не удалась)"
                )
            items.append(record)

        if items:
            emb_list = pd.DataFrame.from_records(items)
        else:
            emb_list = pd.DataFrame.from_records(
                [{"name": "-", "vendor": "-", "default": "-"}]
            )

        return emb_list

    def select_emb(self, emb_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No embedding model is loaded. Please add first", duration=1)
            return ""

        if not ev.selected:
            return ""

        return emb_list["name"][ev.index[0]]

    def on_selected_emb_change(self, selected_emb_name):
        if selected_emb_name == "":
            _check_connection_panel = gr.update(visible=False)
            _selected_panel = gr.update(visible=False)
            _selected_panel_btn = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
            edit_spec = gr.update(value="")
            edit_spec_desc = gr.update(value="")
            edit_default = gr.update(value=False)
            edit_ollama_row = gr.update(visible=False)
            edit_ollama_server = gr.update(choices=[], value=None)
            edit_ollama_model = gr.update(choices=[], value=None)
        else:
            _check_connection_panel = gr.update(visible=True)
            _selected_panel = gr.update(visible=True)
            _selected_panel_btn = gr.update(visible=True)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)

            info = embedding_models_manager.info().get(selected_emb_name)
            if info is None:
                # Embedding failed to load — use spec from DB
                db_item = embedding_models_manager.get_from_db(selected_emb_name)
                if db_item is None:
                    return (
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=True),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(value=""),
                        gr.update(value="Спецификация недоступна"),
                        gr.update(value=False),
                        gr.update(visible=False),
                        gr.update(choices=[], value=None),
                        gr.update(choices=[], value=None),
                    )
                db_spec, db_default = db_item
                info = {
                    "name": selected_emb_name,
                    "spec": deepcopy(db_spec),
                    "default": db_default,
                }
            else:
                info = deepcopy(info)
            spec = info["spec"]
            vendor_str = spec.pop("__type__", "-").split(".")[-1]
            vendor = embedding_models_manager.vendors().get(vendor_str)
            edit_spec_desc = (
                format_description(vendor)
                if vendor
                else f"# {vendor_str}\n\nТип провайдера не найден."
            )

            edit_spec = yaml.dump(spec)
            edit_default = info["default"]

            # Показать ряд Ollama (сервер + модель) только для Ollama-эмбеддингов
            is_ollama = vendor_str == "LCOllamaEmbeddings" or (
                vendor_str == "OpenAIEmbeddings"
                and (
                    spec.get("api_key") == "ollama"
                    or "11434" in str(spec.get("base_url", ""))
                )
            )
            if is_ollama and spec:
                opts = cast(
                    list[tuple[str, str]],
                    ollama_servers_manager.options_for_dropdown() or [],
                )
                server_choices = [c[1] for c in opts]
                current_base = (
                    (spec.get("base_url") or "")
                    .rstrip("/")
                    .replace("/v1", "")
                    .replace("/api", "")
                )
                current_model = spec.get("model") or ""
                # Подобрать текущий сервер по base_url
                server_value = None
                for sid in server_choices:
                    s = ollama_servers_manager.get(sid)
                    if s:
                        b = (
                            (s.get("base_url") or "")
                            .rstrip("/")
                            .replace("/v1", "")
                            .replace("/api", "")
                        )
                        if b == current_base or current_base in b or b in current_base:
                            server_value = sid
                            break
                if not server_value and server_choices:
                    server_value = server_choices[0]
                models = []
                if server_value:
                    base_url = None
                    s = ollama_servers_manager.get(server_value)
                    if s:
                        base_url = s.get("base_url")
                    models = get_ollama_models(base_url=base_url)
                model_choices = [m["name"] for m in models]
                if current_model and current_model not in model_choices:
                    model_choices = [current_model] + model_choices
                edit_ollama_row = gr.update(visible=True)
                edit_ollama_server = gr.update(
                    choices=server_choices, value=server_value
                )
                edit_ollama_model = gr.update(
                    choices=model_choices,
                    value=current_model
                    or (model_choices[0] if model_choices else None),
                )
            else:
                edit_ollama_row = gr.update(visible=False)
                edit_ollama_server = gr.update(choices=[], value=None)
                edit_ollama_model = gr.update(choices=[], value=None)

        return (
            _selected_panel,
            _selected_panel_btn,
            btn_delete,
            btn_delete_yes,
            btn_delete_no,
            edit_spec,
            edit_spec_desc,
            edit_default,
            _check_connection_panel,
            edit_ollama_row,
            edit_ollama_server,
            edit_ollama_model,
        )

    def _on_edit_ollama_model_change(self, model_name: str | None, current_spec: str):
        """Обновить YAML спецификации при смене модели Ollama в панели редактирования."""
        if not model_name:
            return gr.update(value=current_spec)
        try:
            spec = yaml.load(current_spec, Loader=YAMLNoDateSafeLoader) or {}
            spec["model"] = model_name
            return gr.update(value=yaml.dump(spec))
        except Exception:
            return gr.update(value=current_spec)

    def _refresh_edit_ollama_models(self, server_name: str | None):
        """Обновить список моделей Ollama при смене сервера в панели редактирования."""
        if not server_name:
            return gr.update(choices=[], value=None)
        base_url = None
        s = ollama_servers_manager.get(server_name)
        if s:
            base_url = s.get("base_url")
        models = get_ollama_models(base_url=base_url)
        choices = [m["name"] for m in models]
        return gr.update(choices=choices, value=choices[0] if choices else None)

    def on_btn_delete_click(self):
        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def check_connection(self, selected_emb_name, selected_spec):
        from ktem.utils.secret_storage import process_dict_for_load

        log_content: str = ""
        try:
            log_content += f"- Testing model: {selected_emb_name}<br>"
            yield log_content

            info = embedding_models_manager.info().get(selected_emb_name)
            if info is None:
                db_spec = embedding_models_manager.get_spec_from_db(selected_emb_name)
                if db_spec is None:
                    log_content += (
                        "<mark style='color: yellow; background: red'>- Модель не найдена. "
                        "Перезагрузите страницу.</mark><br>"
                    )
                    yield log_content
                    return log_content
                info = {"spec": deepcopy(db_spec)}
            else:
                info = deepcopy(info)

            spec = yaml.load(selected_spec, Loader=YAMLNoDateSafeLoader)
            if spec:
                info["spec"].update(spec)
            process_dict_for_load(info["spec"])

            emb = deserialize(info["spec"], safe=False)

            if emb is None:
                raise Exception(f"Не удалось создать модель: {selected_emb_name}")

            log_content += "- Sending a message `Hi`<br>"
            yield log_content
            _ = emb("Hi")

            log_content += (
                "<mark style='background: green; color: white'>- Connection success. "
                "</mark><br>"
            )
            yield log_content

            gr.Info(f"Embedding {selected_emb_name} connect successfully", duration=1)
        except Exception as e:
            log_content += (
                f"<mark style='color: yellow; background: red'>- Connection failed. "
                f"Got error: {str(e)}</mark><br>"
            )
            yield log_content

        return log_content

    def save_emb(self, selected_emb_name, default, spec):
        try:
            spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
            info = embedding_models_manager.info().get(selected_emb_name)
            if info is not None:
                spec["__type__"] = info["spec"]["__type__"]
            else:
                db_spec = embedding_models_manager.get_spec_from_db(selected_emb_name)
                if db_spec is None:
                    raise ValueError(
                        f'Модель "{selected_emb_name}" не найдена. Перезагрузите страницу.'
                    )
                spec["__type__"] = db_spec.get("__type__")
                if not spec["__type__"]:
                    raise ValueError(
                        f'У модели "{selected_emb_name}" отсутствует __type__ в спецификации.'
                    )
            embedding_models_manager.update(
                selected_emb_name, spec=spec, default=default
            )
            gr.Info(
                f'Save Embedding model "{selected_emb_name}" successfully', duration=1
            )
        except Exception as e:
            gr.Error(
                f'Failed to save Embedding model "{selected_emb_name}": {e}', duration=1
            )

    def delete_emb(self, selected_emb_name):
        try:
            embedding_models_manager.delete(selected_emb_name)
        except Exception as e:
            gr.Error(
                f'Failed to delete Embedding model "{selected_emb_name}": {e}',
                duration=1,
            )
            return selected_emb_name

        return ""

    def refresh_ollama_models(self):
        """Обновить список моделей из Ollama."""
        try:
            models = get_ollama_models()
            if models:
                choices = [model["name"] for model in models]
                return gr.update(choices=choices, value=choices[0] if choices else None)
            else:
                return gr.update(choices=[], value=None)
        except Exception as e:
            gr.Warning(f"Не удалось получить список моделей Ollama: {e}", duration=1)
            return gr.update(choices=[], value=None)

    def on_ollama_model_selected(self, model_name: str, current_spec: str):
        """Заполнить поле model в spec при выборе модели из списка."""
        if not model_name:
            return gr.update(value=current_spec)

        try:
            spec = yaml.load(current_spec, Loader=YAMLNoDateSafeLoader)
            spec["model"] = model_name
            # Если base_url не установлен, предлагаем Ollama URL
            if "base_url" not in spec or not spec.get("base_url"):
                spec["base_url"] = get_ollama_base_url().replace("/api", "/v1/")
            # Устанавливаем api_key для Ollama если не установлен
            if "api_key" not in spec or not spec.get("api_key"):
                spec["api_key"] = "ollama"
            return gr.update(value=yaml.dump(spec))
        except Exception:
            return gr.update(value=current_spec)

    def pull_ollama_model_ui(
        self,
        server_name: str | None,
        dropdown_model: str | None,
        input_model: str | None,
    ):
        """Загрузить модель из Ollama с отображением прогресса. Модель берётся из выпадающего списка или поля ввода."""
        model_name = (input_model or "").strip() or (dropdown_model or "").strip()
        if not model_name:
            gr.Warning("Выберите модель из списка или введите имя вручную", duration=1)
            yield gr.update(visible=False, value=""), gr.update()
            return

        base_url = None
        if server_name:
            s = ollama_servers_manager.get(server_name)
            if s:
                base_url = s.get("base_url")

        progress_html = "<div style='padding: 10px;'>"
        progress_html += f"<p>Загрузка модели <strong>{model_name}</strong>...</p>"
        yield gr.update(visible=True, value=progress_html), gr.update()

        try:
            for response in pull_ollama_model(base_url=base_url, model_name=model_name):
                status = response.get("status", "")
                completed = response.get("completed", 0)
                total = response.get("total", 0)

                if completed > 0 and total > 0:
                    ratio = int(completed / total * 100)
                    progress_html = f"""
                    <div style='padding: 10px;'>
                        <p>Загрузка модели <strong>{model_name}</strong>...</p>
                        <p>{status}: {ratio}%</p>
                        <progress value='{completed}' max='{total}' style='width: 100%;'></progress>
                    </div>
                    """
                else:
                    progress_html = f"""
                    <div style='padding: 10px;'>
                        <p>Загрузка модели <strong>{model_name}</strong>...</p>
                        <p>{status}</p>
                    </div>
                    """

                yield gr.update(visible=True, value=progress_html), gr.update()

                if status == "success":
                    progress_html = f"""
                    <div style='padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;'>
                        <p><strong>✓ Модель {model_name} успешно загружена!</strong></p>
                    </div>
                    """
                    gr.Info(f"Модель {model_name} успешно загружена", duration=1)
                    # Обновить список моделей для выбранного сервера
                    models = get_ollama_models(base_url=base_url)
                    choices = [m["name"] for m in models]
                    yield (
                        gr.update(visible=True, value=progress_html),
                        gr.update(choices=choices, value=model_name),
                    )
                    return

            # Если дошли сюда без success
            progress_html = """
            <div style='padding: 10px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px;'>
                <p>Загрузка завершена, но статус не определен</p>
            </div>
            """
            yield gr.update(visible=True, value=progress_html), gr.update()

        except Exception as e:
            error_html = f"""
            <div style='padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;'>
                <p><strong>Ошибка при загрузке модели:</strong></p>
                <p>{str(e)}</p>
            </div>
            """
            gr.Error(f"Ошибка при загрузке модели: {e}", duration=1)
            yield gr.update(visible=True, value=error_html), gr.update()
