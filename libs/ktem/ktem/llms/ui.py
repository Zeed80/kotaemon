from copy import deepcopy

import gradio as gr
import pandas as pd
import yaml
from ktem.app import BasePage
from ktem.utils.file import YAMLNoDateSafeLoader
from ktem.utils.ollama import (
    get_ollama_base_url,
    get_ollama_base_url_for_langchain,
    get_ollama_models,
    pull_ollama_model,
)
from theflow.utils.modules import deserialize

from .manager import llms


def format_description(cls):
    params = cls.describe()["params"]
    params_lines = ["| Name | Type | Description |", "| --- | --- | --- |"]
    for key, value in params.items():
        if isinstance(value["auto_callback"], str):
            continue
        params_lines.append(f"| {key} | {value['type']} | {value['help']} |")
    return f"{cls.__doc__}\n\n" + "\n".join(params_lines)


class LLMManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.spec_desc_default = (
            "# Spec description\n\nSelect an LLM to view the spec description."
        )
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.llm_list = gr.DataFrame(
                headers=["name", "vendor", "default"],
                interactive=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_llm_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_default = gr.Checkbox(
                            label="Set default",
                            info=(
                                "Set this LLM as default. If no default is set, a "
                                "random LLM will be used."
                            ),
                        )
                        self.edit_spec = gr.Textbox(
                            label="Specification",
                            info="Specification of the LLM in YAML format",
                            lines=10,
                        )

                        with gr.Accordion(
                            label="Test connection", visible=False, open=False
                        ) as self._check_connection_panel:
                            with gr.Row():
                                with gr.Column(scale=4):
                                    self.connection_logs = gr.HTML("Logs")

                                with gr.Column(scale=1):
                                    self.btn_test_connection = gr.Button(
                                        "Test",
                                    )

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
                        label="LLM name",
                        info=(
                            "Must be unique. The name will be used to identify the LLM."
                        ),
                    )
                    self.llm_choices = gr.Dropdown(
                        label="LLM vendors",
                        info=(
                            "Choose the vendor for the LLM. Each vendor has different "
                            "specification."
                        ),
                    )
                    self.spec = gr.Textbox(
                        label="Specification",
                        info="Specification of the LLM in YAML format",
                    )
                    self.default = gr.Checkbox(
                        label="Set default",
                        info=(
                            "Set this LLM as default. This default LLM will be used "
                            "by default across the application."
                        ),
                    )
                    self.btn_new = gr.Button("Add LLM", variant="primary")

                    # Ollama-specific UI elements
                    with gr.Column(visible=False) as self.ollama_section:
                        gr.Markdown("### Ollama Model Selection")
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
                            placeholder="e.g., llama3.1:8b",
                        )
                        with gr.Row():
                            self.btn_pull_ollama_model = gr.Button(
                                "⬇️ Pull Model", variant="secondary"
                            )
                            self.ollama_pull_progress = gr.HTML(
                                visible=False, value=""
                            )

                with gr.Column(scale=3):
                    self.spec_desc = gr.Markdown(self.spec_desc_default)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_llms,
            inputs=[],
            outputs=[self.llm_list],
        )
        self._app.app.load(
            lambda: gr.update(choices=list(llms.vendors().keys())),
            outputs=[self.llm_choices],
        )
        # Load Ollama models on startup if available
        self._app.app.load(
            self.refresh_ollama_models,
            inputs=[],
            outputs=[self.ollama_model_dropdown],
        )

    def on_llm_vendor_change(self, vendor):
        vendor_cls = llms.vendors()[vendor]
        vendor_name = vendor_cls.__name__

        required: dict = {}
        desc = vendor_cls.describe()
        for key, value in desc["params"].items():
            if value.get("required", False):
                required[key] = None

        # Check if this is LCOllamaChat vendor
        is_ollama = vendor_name == "LCOllamaChat"

        # Auto-fill base_url for Ollama
        if is_ollama:
            # LCOllamaChat использует langchain_ollama.ChatOllama, который ожидает
            # базовый URL без /api и без /v1/, например: http://localhost:11434/
            base_url = get_ollama_base_url_for_langchain()
            required["base_url"] = base_url
            # Set default num_ctx if not present
            if "num_ctx" not in required:
                required["num_ctx"] = 8192

        spec_yaml = yaml.dump(required)
        desc_markdown = format_description(vendor_cls)

        return (
            spec_yaml,
            desc_markdown,
            gr.update(visible=is_ollama),
            gr.update(value=""),
            gr.update(value=""),
        )

    def on_register_events(self):
        self.llm_choices.select(
            self.on_llm_vendor_change,
            inputs=[self.llm_choices],
            outputs=[
                self.spec,
                self.spec_desc,
                self.ollama_section,
                self.ollama_model_dropdown,
                self.ollama_model_input,
            ],
        )
        self.btn_refresh_ollama_models.click(
            self.refresh_ollama_models,
            inputs=[],
            outputs=[self.ollama_model_dropdown],
        )
        self.ollama_model_dropdown.change(
            self.on_ollama_model_selected,
            inputs=[self.ollama_model_dropdown, self.spec],
            outputs=[self.spec],
        )
        self.btn_pull_ollama_model.click(
            self.pull_ollama_model_ui,
            inputs=[self.ollama_model_input],
            outputs=[self.ollama_pull_progress, self.ollama_model_dropdown],
        )
        self.btn_new.click(
            self.create_llm,
            inputs=[self.name, self.llm_choices, self.spec, self.default],
            outputs=[],
        ).success(self.list_llms, inputs=[], outputs=[self.llm_list]).success(
            lambda: ("", None, "", False, self.spec_desc_default),
            outputs=[
                self.name,
                self.llm_choices,
                self.spec,
                self.default,
                self.spec_desc,
            ],
        )
        self.llm_list.select(
            self.select_llm,
            inputs=self.llm_list,
            outputs=[self.selected_llm_name],
            show_progress="hidden",
        )
        self.selected_llm_name.change(
            self.on_selected_llm_change,
            inputs=[self.selected_llm_name],
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
                # check connection panel
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
            self.delete_llm,
            inputs=[self.selected_llm_name],
            outputs=[self.selected_llm_name],
            show_progress="hidden",
        ).then(
            self.list_llms,
            inputs=[],
            outputs=[self.llm_list],
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
            self.save_llm,
            inputs=[
                self.selected_llm_name,
                self.edit_default,
                self.edit_spec,
            ],
            show_progress="hidden",
        ).then(
            self.list_llms,
            inputs=[],
            outputs=[self.llm_list],
        )
        self.btn_close.click(
            lambda: "",
            outputs=[self.selected_llm_name],
        )

        self.btn_test_connection.click(
            self.check_connection,
            inputs=[self.selected_llm_name, self.edit_spec],
            outputs=[self.connection_logs],
        )

    def create_llm(self, name, choices, spec, default):
        try:
            spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
            spec["__type__"] = (
                llms.vendors()[choices].__module__
                + "."
                + llms.vendors()[choices].__qualname__
            )

            llms.add(name, spec=spec, default=default)
            gr.Info(f"LLM {name} created successfully")
        except Exception as e:
            raise gr.Error(f"Failed to create LLM {name}: {e}")

    def list_llms(self):
        """List the LLMs"""
        items = []
        for item in llms.info().values():
            record = {}
            record["name"] = item["name"]
            record["vendor"] = item["spec"].get("__type__", "-").split(".")[-1]
            record["default"] = item["default"]
            items.append(record)

        if items:
            llm_list = pd.DataFrame.from_records(items)
        else:
            llm_list = pd.DataFrame.from_records(
                [{"name": "-", "vendor": "-", "default": "-"}]
            )

        return llm_list

    def select_llm(self, llm_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No LLM is loaded. Please add LLM first")
            return ""

        if not ev.selected:
            return ""

        return llm_list["name"][ev.index[0]]

    def on_selected_llm_change(self, selected_llm_name):
        if selected_llm_name == "":
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

            info = deepcopy(llms.info()[selected_llm_name])
            vendor_str = info["spec"].pop("__type__", "-").split(".")[-1]
            vendor = llms.vendors()[vendor_str]

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

    def check_connection(self, selected_llm_name: str, selected_spec):
        log_content: str = ""

        try:
            log_content += f"- Testing model: {selected_llm_name}<br>"
            yield log_content

            # Parse content & init model
            info = deepcopy(llms.info()[selected_llm_name])

            # Parse content & create dummy embedding
            spec = yaml.load(selected_spec, Loader=YAMLNoDateSafeLoader)
            info["spec"].update(spec)

            llm = deserialize(info["spec"], safe=False)

            if llm is None:
                raise Exception(f"Can not found model: {selected_llm_name}")

            log_content += "- Sending a message `Hi`<br>"
            yield log_content
            respond = llm("Hi")

            log_content += (
                f"<mark style='background: green; color: white'>- Connection success. "
                f"Got response:\n {respond}</mark><br>"
            )
            yield log_content

            gr.Info(f"LLM {selected_llm_name} connect successfully")
        except Exception as e:
            log_content += (
                f"<mark style='color: yellow; background: red'>- Connection failed. "
                f"Got error:\n {e}</mark>"
            )
            yield log_content

        return log_content

    def save_llm(self, selected_llm_name, default, spec):
        try:
            spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
            spec["__type__"] = llms.info()[selected_llm_name]["spec"]["__type__"]
            llms.update(selected_llm_name, spec=spec, default=default)
            gr.Info(f"LLM {selected_llm_name} saved successfully")
        except Exception as e:
            raise gr.Error(f"Failed to save LLM {selected_llm_name}: {e}")

    def delete_llm(self, selected_llm_name):
        try:
            llms.delete(selected_llm_name)
        except Exception as e:
            gr.Error(f"Failed to delete LLM {selected_llm_name}: {e}")
            return selected_llm_name

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
            gr.Warning(f"Не удалось получить список моделей Ollama: {e}")
            return gr.update(choices=[], value=None)

    def on_ollama_model_selected(self, model_name: str, current_spec: str):
        """Заполнить поле model в spec при выборе модели из списка."""
        if not model_name:
            return gr.update(value=current_spec)

        try:
            spec = yaml.load(current_spec, Loader=YAMLNoDateSafeLoader)
            spec["model"] = model_name
            # Также обновим base_url если его нет
            # Проверяем тип вендора из spec, чтобы использовать правильный формат URL
            vendor_type = spec.get("__type__", "")
            if "LCOllamaChat" in vendor_type:
                # LCOllamaChat использует langchain_ollama, нужен URL без /api
                if "base_url" not in spec:
                    spec["base_url"] = get_ollama_base_url_for_langchain()
            else:
                # Для других вендоров (например, ChatOpenAI с Ollama) используем стандартный формат
                if "base_url" not in spec:
                    spec["base_url"] = get_ollama_base_url()
            return gr.update(value=yaml.dump(spec))
        except Exception:
            return gr.update(value=current_spec)

    def pull_ollama_model_ui(self, model_name: str):
        """Загрузить модель из Ollama с отображением прогресса."""
        if not model_name:
            gr.Warning("Введите имя модели для загрузки")
            yield gr.update(visible=False, value=""), gr.update()
            return

        progress_html = "<div style='padding: 10px;'>"
        progress_html += f"<p>Загрузка модели <strong>{model_name}</strong>...</p>"
        yield gr.update(visible=True, value=progress_html), gr.update()

        try:
            for response in pull_ollama_model(model_name=model_name):
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
                    gr.Info(f"Модель {model_name} успешно загружена")
                    # Обновить список моделей
                    models = get_ollama_models()
                    choices = [m["name"] for m in models]
                    yield gr.update(visible=True, value=progress_html), gr.update(
                        choices=choices, value=model_name
                    )
                    return

            # Если дошли сюда без success
            progress_html = f"""
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
            gr.Error(f"Ошибка при загрузке модели: {e}")
            yield gr.update(visible=True, value=error_html), gr.update()
