from copy import deepcopy
from typing import cast

import gradio as gr
import pandas as pd
import yaml
from theflow.utils.modules import deserialize

from kotaemon.base import Document
from kotaemon.rerankings import OllamaReranking
from ktem.app import BasePage
from ktem.ollama_servers import ollama_servers_manager
from ktem.utils.file import YAMLNoDateSafeLoader
from ktem.utils.ollama import (
    check_ollama_embed_model,
    get_ollama_models,
    pull_ollama_model,
)

from .manager import reranking_models_manager


def format_description(cls):
    params = cls.describe()["params"]
    params_lines = ["| Name | Type | Description |", "| --- | --- | --- |"]
    for key, value in params.items():
        if isinstance(value["auto_callback"], str):
            continue
        params_lines.append(f"| {key} | {value['type']} | {value['help']} |")
    return f"{cls.__doc__}\n\n" + "\n".join(params_lines)


class RerankingManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.spec_desc_default = (
            "# Spec description\n\nSelect a model to view the spec description."
        )
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.rerank_list = gr.DataFrame(
                headers=["name", "vendor", "default"],
                interactive=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_rerank_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_default = gr.Checkbox(
                            label="Set default",
                            info=(
                                "Set this Reranking model as default. This default "
                                "Reranking will be used by other components by default "
                                "if no Reranking is specified for such components."
                            ),
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
                            "The name will be used to identify the reranking model."
                        ),
                    )
                    self.rerank_choices = gr.Dropdown(
                        label="Vendors",
                        info=(
                            "Choose the vendor of the Reranking model. Each vendor "
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
                            "Set this Reranking model as default. This default "
                            "Reranking will be used by other components by default "
                            "if no Reranking is specified for such components."
                        ),
                    )
                    self.btn_new = gr.Button("Add", variant="primary")

                    # Ollama section
                    with gr.Column(visible=False) as self.ollama_section:
                        gr.Markdown("### Ollama")
                        self.ollama_server = gr.Dropdown(
                            label="Ollama server",
                            choices=[],
                            value=None,
                            info="Choose a registered Ollama server",
                        )
                        with gr.Row():
                            self.ollama_model = gr.Dropdown(
                                label="Model",
                                choices=[],
                                value=None,
                                allow_custom_value=True,
                            )
                            self.btn_refresh_ollama = gr.Button("🔄 Refresh", scale=0)
                        self.ollama_model_input = gr.Textbox(
                            label="Or enter model name",
                            placeholder="e.g., qwen3-reranker",
                        )
                        self.btn_pull_ollama = gr.Button(
                            "⬇️ Pull Model", variant="secondary"
                        )
                        self.ollama_pull_progress = gr.HTML(visible=False)

                    # Cohere section
                    with gr.Column(visible=False) as self.cohere_section:
                        gr.Markdown("### Cohere")
                        self.cohere_model = gr.Dropdown(
                            label="Model",
                            choices=["rerank-multilingual-v2.0", "rerank-english-v2.0"],
                            value="rerank-multilingual-v2.0",
                            allow_custom_value=True,
                        )
                        self.cohere_api_key = gr.Textbox(
                            label="API Key",
                            type="password",
                            placeholder="...",
                        )

                    # Voyage section
                    with gr.Column(visible=False) as self.voyage_section:
                        gr.Markdown("### VoyageAI")
                        self.voyage_model = gr.Dropdown(
                            label="Model",
                            choices=["rerank-2", "rerank-lite-1"],
                            value="rerank-2",
                            allow_custom_value=True,
                        )
                        self.voyage_api_key = gr.Textbox(
                            label="API Key",
                            type="password",
                            placeholder="...",
                        )

                    # Tei section
                    with gr.Column(visible=False) as self.tei_section:
                        gr.Markdown("### TeiFastReranking (TEI)")
                        self.tei_endpoint = gr.Textbox(
                            label="Endpoint URL",
                            placeholder="http://localhost:8080",
                        )
                        self.tei_model = gr.Textbox(
                            label="Model name (optional)",
                            placeholder="",
                        )

                with gr.Column(scale=3):
                    self.spec_desc = gr.Markdown(self.spec_desc_default)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_rerankings,
            inputs=[],
            outputs=[self.rerank_list],
        )
        self._app.app.load(
            lambda: gr.update(choices=list(reranking_models_manager.vendors().keys())),
            outputs=[self.rerank_choices],
        )

        def _ollama_server_choices() -> list[str]:
            opts = cast(
                list[tuple[str, str]],
                ollama_servers_manager.options_for_dropdown() or [],
            )
            return [c[1] for c in opts]

        self._app.app.load(
            lambda: gr.update(choices=_ollama_server_choices()),
            outputs=[self.ollama_server],
        )

    def refresh_ollama_models(self, server_name):
        """Refresh Ollama reranker models list."""
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

    def on_ollama_server_change(self, server_name, current_spec):
        """Update spec when Ollama server changes."""
        if not server_name:
            return gr.update(), gr.update()
        s = ollama_servers_manager.get(server_name)
        if not s:
            return gr.update(), gr.update()
        base_url = s["base_url"].rstrip("/").replace("/v1", "")
        try:
            spec = yaml.load(current_spec, Loader=YAMLNoDateSafeLoader) or {}
            spec["base_url"] = base_url
            models = get_ollama_models(s["base_url"])
            choices = [m["name"] for m in models] if models else []
            return (
                gr.update(value=yaml.dump(spec)),
                gr.update(choices=choices, value=choices[0] if choices else None),
            )
        except Exception:
            return gr.update(), gr.update()

    def on_ollama_model_selected(self, model_name, current_spec):
        """Update spec model when Ollama model selected."""
        if not model_name:
            return gr.update()
        try:
            spec = yaml.load(current_spec, Loader=YAMLNoDateSafeLoader) or {}
            spec["model_name"] = model_name
            return gr.update(value=yaml.dump(spec))
        except Exception:
            return gr.update()

    def pull_ollama_rerank_ui(self, server_name, model_name):
        """Pull Ollama reranker model."""
        if not model_name:
            gr.Warning("Введите имя модели", duration=1)
            yield gr.update(visible=False), gr.update()
            return
        base_url = None
        if server_name:
            s = ollama_servers_manager.get(server_name)
            if s:
                base_url = s["base_url"]
        progress = "<p>Загрузка...</p>"
        yield gr.update(visible=True, value=progress), gr.update()
        try:
            for _ in pull_ollama_model(base_url=base_url, model_name=model_name):
                yield gr.update(visible=True, value=progress), gr.update()
            models = get_ollama_models(base_url)
            choices = [m["name"] for m in models] if models else []
            gr.Info(f"Модель {model_name} загружена", duration=1)
            yield (
                gr.update(visible=True, value=f"<p>Готово: {model_name}</p>"),
                gr.update(choices=choices, value=model_name),
            )
        except Exception as e:
            gr.Error(str(e), duration=1)
            yield gr.update(visible=True, value=f"<p>Ошибка: {e}</p>"), gr.update()

    def on_rerank_vendor_change(self, vendor):
        vendor_cls = reranking_models_manager.vendors().get(vendor)
        if not vendor_cls:
            return (
                "",
                self.spec_desc_default,
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(choices=[], value=None),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value="rerank-multilingual-v2.0"),
                gr.update(value=""),
                gr.update(value="rerank-2"),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
            )
        required: dict = {}
        desc = vendor_cls.describe()
        for key, value in desc["params"].items():
            if value.get("required", False):
                required[key] = value.get("default", None)
        spec_yaml = yaml.dump(required)
        desc_markdown = format_description(vendor_cls)

        vendor_name = vendor_cls.__name__
        is_ollama = vendor_name == "OllamaReranking"
        is_cohere = vendor_name == "CohereReranking"
        is_voyage = vendor_name == "VoyageAIReranking"
        is_tei = vendor_name == "TeiFastReranking"

        opts = cast(
            list[tuple[str, str]],
            ollama_servers_manager.options_for_dropdown() or [],
        )
        server_choices = [c[1] for c in opts]
        server_value = server_choices[0] if server_choices else None
        model_choices = []
        if is_ollama and server_value:
            s = ollama_servers_manager.get(server_value)
            if s:
                models = get_ollama_models(s["base_url"])
                model_choices = [m["name"] for m in models] if models else []

        return (
            spec_yaml,
            desc_markdown,
            gr.update(visible=is_ollama),
            gr.update(visible=is_cohere),
            gr.update(visible=is_voyage),
            gr.update(visible=is_tei),
            gr.update(choices=server_choices, value=server_value),
            gr.update(
                choices=model_choices, value=model_choices[0] if model_choices else None
            ),
            gr.update(value=""),
            gr.update(value="rerank-multilingual-v2.0"),
            gr.update(value=""),
            gr.update(value="rerank-2"),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
        )

    def on_register_events(self):
        self.rerank_choices.select(
            self.on_rerank_vendor_change,
            inputs=[self.rerank_choices],
            outputs=[
                self.spec,
                self.spec_desc,
                self.ollama_section,
                self.cohere_section,
                self.voyage_section,
                self.tei_section,
                self.ollama_server,
                self.ollama_model,
                self.ollama_model_input,
                self.cohere_model,
                self.cohere_api_key,
                self.voyage_model,
                self.voyage_api_key,
                self.tei_endpoint,
                self.tei_model,
            ],
        )
        self.ollama_server.change(
            self.on_ollama_server_change,
            inputs=[self.ollama_server, self.spec],
            outputs=[self.spec, self.ollama_model],
        )
        self.btn_refresh_ollama.click(
            self.refresh_ollama_models,
            inputs=[self.ollama_server],
            outputs=[self.ollama_model],
        )
        self.ollama_model.change(
            self.on_ollama_model_selected,
            inputs=[self.ollama_model, self.spec],
            outputs=[self.spec],
        )
        self.btn_pull_ollama.click(
            self.pull_ollama_rerank_ui,
            inputs=[self.ollama_server, self.ollama_model_input],
            outputs=[self.ollama_pull_progress, self.ollama_model],
        )
        self.btn_new.click(
            self.create_rerank,
            inputs=[
                self.name,
                self.rerank_choices,
                self.spec,
                self.default,
                self.ollama_server,
                self.ollama_model,
                self.ollama_model_input,
                self.cohere_model,
                self.cohere_api_key,
                self.voyage_model,
                self.voyage_api_key,
                self.tei_endpoint,
                self.tei_model,
            ],
            outputs=None,
        ).success(self.list_rerankings, inputs=[], outputs=[self.rerank_list]).success(
            lambda: (
                "",
                None,
                "",
                False,
                self.spec_desc_default,
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                None,
                "",
                "",
                "rerank-multilingual-v2.0",
                "",
                "rerank-2",
                "",
                "",
                "",
            ),
            outputs=[
                self.name,
                self.rerank_choices,
                self.spec,
                self.default,
                self.spec_desc,
                self.ollama_section,
                self.cohere_section,
                self.voyage_section,
                self.tei_section,
                self.ollama_server,
                self.ollama_model,
                self.ollama_model_input,
                self.cohere_model,
                self.cohere_api_key,
                self.voyage_model,
                self.voyage_api_key,
                self.tei_endpoint,
                self.tei_model,
            ],
        )
        self.rerank_list.select(
            self.select_rerank,
            inputs=self.rerank_list,
            outputs=[self.selected_rerank_name],
            show_progress="hidden",
        )
        self.selected_rerank_name.change(
            self.on_selected_rerank_change,
            inputs=[self.selected_rerank_name],
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
            ],
            show_progress="hidden",
        ).success(lambda: gr.update(value=""), outputs=[self.connection_logs])

        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_rerank,
            inputs=[self.selected_rerank_name],
            outputs=[self.selected_rerank_name],
            show_progress="hidden",
        ).then(
            self.list_rerankings,
            inputs=[],
            outputs=[self.rerank_list],
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
            self.save_rerank,
            inputs=[
                self.selected_rerank_name,
                self.edit_default,
                self.edit_spec,
            ],
            show_progress="hidden",
        ).then(
            self.list_rerankings,
            inputs=[],
            outputs=[self.rerank_list],
        )
        self.btn_close.click(lambda: "", outputs=[self.selected_rerank_name])

        self.btn_test_connection.click(
            self.check_connection,
            inputs=[self.selected_rerank_name, self.edit_spec],
            outputs=[self.connection_logs],
        )

    def create_rerank(
        self,
        name,
        choices,
        spec,
        default,
        ollama_server=None,
        ollama_model=None,
        ollama_model_input=None,
        cohere_model=None,
        cohere_api_key=None,
        voyage_model=None,
        voyage_api_key=None,
        tei_endpoint=None,
        tei_model=None,
    ):
        try:
            vendor_cls = reranking_models_manager.vendors().get(choices)
            if not vendor_cls:
                raise gr.Error("Выберите провайдера")
            type_str = vendor_cls.__module__ + "." + vendor_cls.__qualname__
            vendor_name = vendor_cls.__name__

            if vendor_name == "OllamaReranking" and ollama_server:
                s = ollama_servers_manager.get(ollama_server)
                if s:
                    model = (ollama_model or "").strip() or (
                        ollama_model_input or ""
                    ).strip()
                    if not model:
                        raise gr.Error("Выберите или введите модель Ollama")
                    base_url = s["base_url"].rstrip("/").replace("/v1", "")
                    spec = {
                        "__type__": type_str,
                        "base_url": base_url,
                        "model_name": model,
                    }
                else:
                    spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
                    spec["__type__"] = type_str
            elif vendor_name == "CohereReranking" and (cohere_model or cohere_api_key):
                spec = {
                    "__type__": type_str,
                    "model_name": (cohere_model or "rerank-multilingual-v2.0").strip(),
                    "cohere_api_key": (cohere_api_key or "").strip() or None,
                }
                if not spec["cohere_api_key"]:
                    raise gr.Error("Введите Cohere API ключ")
            elif vendor_name == "VoyageAIReranking" and (
                voyage_model or voyage_api_key
            ):
                spec = {
                    "__type__": type_str,
                    "model_name": (voyage_model or "rerank-2").strip(),
                    "api_key": (voyage_api_key or "").strip() or None,
                }
                if not spec["api_key"]:
                    raise gr.Error("Введите VoyageAI API ключ")
            elif vendor_name == "TeiFastReranking" and tei_endpoint:
                spec = {
                    "__type__": type_str,
                    "endpoint_url": tei_endpoint.strip(),
                    "model_name": (tei_model or "").strip() or None,
                }
            else:
                spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
                spec["__type__"] = type_str

            reranking_models_manager.add(name, spec=spec, default=default)
            gr.Info(f'Create Reranking model "{name}" successfully', duration=1)
        except gr.Error:
            raise
        except Exception as e:
            raise gr.Error(f"Failed to create Reranking model {name}: {e}")

    def list_rerankings(self):
        """List the Reranking models"""
        items = []
        for item in reranking_models_manager.info().values():
            record = {}
            record["name"] = item["name"]
            record["vendor"] = item["spec"].get("__type__", "-").split(".")[-1]
            record["default"] = item["default"]
            items.append(record)

        if items:
            rerank_list = pd.DataFrame.from_records(items)
        else:
            rerank_list = pd.DataFrame.from_records(
                [{"name": "-", "vendor": "-", "default": "-"}]
            )

        return rerank_list

    def select_rerank(self, rerank_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No reranking model is loaded. Please add first", duration=1)
            return ""

        if not ev.selected:
            return ""

        return rerank_list["name"][ev.index[0]]

    def on_selected_rerank_change(self, selected_rerank_name):
        if selected_rerank_name == "":
            _check_connection_panel = gr.update(visible=False)
            _selected_panel = gr.update(visible=False)
            _selected_panel_btn = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
            edit_spec = gr.update(value="")
            edit_spec_desc = gr.update(value="")
            edit_default = gr.update(value=False)
        else:
            _check_connection_panel = gr.update(visible=True)
            _selected_panel = gr.update(visible=True)
            _selected_panel_btn = gr.update(visible=True)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)

            info = deepcopy(reranking_models_manager.info()[selected_rerank_name])
            vendor_str = info["spec"].pop("__type__", "-").split(".")[-1]
            vendor = reranking_models_manager.vendors()[vendor_str]

            edit_spec = yaml.dump(info["spec"])
            edit_spec_desc = format_description(vendor)
            edit_default = info["default"]

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
        )

    def on_btn_delete_click(self):
        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def check_connection(self, selected_rerank_name, selected_spec):
        log_content: str = ""
        try:
            log_content += f"- Testing model: {selected_rerank_name}<br>"
            yield log_content

            # Parse content & init model
            info = deepcopy(reranking_models_manager.info()[selected_rerank_name])

            # Parse content & create dummy response
            spec = yaml.load(selected_spec, Loader=YAMLNoDateSafeLoader)
            info["spec"].update(spec)

            rerank = deserialize(info["spec"], safe=False)

            if rerank is None:
                raise Exception(f"Can not found model: {selected_rerank_name}")

            if isinstance(rerank, OllamaReranking):
                log_content += (
                    "- Ollama reranker: проверка наличия модели и /api/embed<br>"
                )
                yield log_content
                check_ollama_embed_model(
                    base_url=(rerank.base_url or "").strip() or None,
                    model_name=rerank.model_name,
                )
                log_content += (
                    "<mark style='background: green; color: white'>- Connection success. "
                    "Модель найдена и поддерживает embed.</mark><br>"
                )
                yield log_content
                gr.Info(
                    f"Reranker {selected_rerank_name} connect successfully",
                    duration=1,
                )
                return log_content

            log_content += "- Sending a message ([`Hello`], `Hi`)<br>"
            yield log_content
            _ = rerank([Document(content="Hello")], "Hi")

            log_content += (
                "<mark style='background: green; color: white'>- Connection success. "
                "</mark><br>"
            )
            yield log_content

            gr.Info(
                f"Embedding {selected_rerank_name} connect successfully", duration=1
            )
        except Exception as e:
            print(e)
            log_content += (
                f"<mark style='color: yellow; background: red'>- Connection failed. "
                f"Got error:\n {str(e)}</mark>"
            )
            yield log_content

        return log_content

    def save_rerank(self, selected_rerank_name, default, spec):
        try:
            spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
            spec["__type__"] = reranking_models_manager.info()[selected_rerank_name][
                "spec"
            ]["__type__"]
            reranking_models_manager.update(
                selected_rerank_name, spec=spec, default=default
            )
            gr.Info(
                f'Save Reranking model "{selected_rerank_name}" successfully',
                duration=1,
            )
        except Exception as e:
            gr.Error(
                f'Failed to save Embedding model "{selected_rerank_name}": {e}',
                duration=1,
            )

    def delete_rerank(self, selected_rerank_name):
        try:
            reranking_models_manager.delete(selected_rerank_name)
        except Exception as e:
            gr.Error(
                f'Failed to delete Reranking model "{selected_rerank_name}": {e}',
                duration=1,
            )
            return selected_rerank_name

        return ""
