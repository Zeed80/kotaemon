"""UI вкладки «VLMs» в Resources: список, добавление, редактирование, удаление."""

import gradio as gr
import pandas as pd
from ktem.app import BasePage

from ktem.ollama_servers import ollama_servers_manager
from ktem.vlms import vlms_manager

PROVIDERS = [
    ("Azure OpenAI Vision", "azure_openai"),
    ("OpenAI Vision", "openai"),
    ("Ollama Vision", "ollama"),
]


class VLMsManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.vlm_list = gr.DataFrame(
                headers=["name", "provider"],
                interactive=False,
                label="Vision models (VLM)",
            )
            with gr.Column(visible=False) as self._edit_panel:
                self.edit_name = gr.Textbox(label="Имя", interactive=False)
                self.edit_provider = gr.Dropdown(
                    label="Провайдер",
                    choices=[p[1] for p in PROVIDERS],
                    value="azure_openai",
                )
                self.edit_endpoint_url = gr.Textbox(
                    label="Endpoint URL",
                    visible=True,
                    info="URL chat/completions (Azure/OpenAI)",
                )
                self.edit_model = gr.Textbox(label="Модель", visible=True)
                self.edit_api_key = gr.Textbox(
                    label="API key (optional)",
                    type="password",
                    visible=True,
                )
                self.edit_ollama_server = gr.Dropdown(
                    label="Ollama server",
                    choices=[],
                    value=None,
                    visible=False,
                )
                self.edit_ollama_model = gr.Textbox(
                    label="Модель Ollama",
                    value="llava",
                    visible=False,
                )
                with gr.Row():
                    self.btn_save = gr.Button("Сохранить", variant="primary")
                    self.btn_delete = gr.Button("Удалить", variant="stop")
                    self.btn_delete_confirm = gr.Button(
                        "Подтвердить удаление",
                        variant="stop",
                        visible=False,
                    )
                    self.btn_delete_cancel = gr.Button("Отмена", visible=False)
                    self.btn_close_edit = gr.Button("Закрыть")
                self.selected_vlm_name = gr.Textbox(value="", visible=False)

        with gr.Tab(label="Add"):
            self.add_name = gr.Textbox(
                label="Имя",
                info="Уникальное имя VLM (например: gpt4o, llava-local)",
            )
            self.add_provider = gr.Dropdown(
                label="Провайдер",
                choices=[p[1] for p in PROVIDERS],
                value="azure_openai",
            )
            self.add_endpoint_url = gr.Textbox(
                label="Endpoint URL",
                info="URL chat/completions (Azure/OpenAI)",
                placeholder="https://.../openai/deployments/.../chat/completions?api-version=...",
            )
            self.add_model = gr.Textbox(
                label="Модель",
                placeholder="gpt-4o",
            )
            self.add_api_key = gr.Textbox(
                label="API key (optional)",
                type="password",
            )
            self.add_ollama_server = gr.Dropdown(
                label="Ollama server",
                choices=[],
                value=None,
                visible=False,
            )
            self.add_ollama_model = gr.Textbox(
                label="Модель Ollama",
                placeholder="llava",
                visible=False,
            )
            self.btn_add = gr.Button("Добавить VLM", variant="primary")

    def _on_app_created(self):
        self._app.app.load(
            self.list_vlms,
            inputs=[],
            outputs=[self.vlm_list],
            show_progress="hidden",
        )
        self._app.app.load(
            lambda: gr.update(
                choices=[c[1] for c in ollama_servers_manager.options_for_dropdown()]
            ),
            outputs=[self.add_ollama_server],
            show_progress="hidden",
        )

    def list_vlms(self):
        rows = vlms_manager.list()
        if not rows:
            return pd.DataFrame(columns=["name", "provider"])
        data = [
            {
                "name": v["name"],
                "provider": (v.get("spec") or {}).get("provider", "—"),
            }
            for v in rows
        ]
        return pd.DataFrame(data)

    def on_register_events(self):
        self.vlm_list.select(
            self.on_select_vlm,
            inputs=[self.vlm_list],
            outputs=[
                self._edit_panel,
                self.edit_name,
                self.edit_provider,
                self.edit_endpoint_url,
                self.edit_model,
                self.edit_api_key,
                self.edit_ollama_server,
                self.edit_ollama_model,
                self.selected_vlm_name,
            ],
            show_progress="hidden",
        )
        self.add_provider.change(
            self.on_add_provider_change,
            inputs=[self.add_provider],
            outputs=[
                self.add_endpoint_url,
                self.add_model,
                self.add_api_key,
                self.add_ollama_server,
                self.add_ollama_model,
            ],
            show_progress="hidden",
        )
        self.edit_provider.change(
            self.on_edit_provider_change,
            inputs=[self.edit_provider],
            outputs=[
                self.edit_endpoint_url,
                self.edit_model,
                self.edit_api_key,
                self.edit_ollama_server,
                self.edit_ollama_model,
            ],
            show_progress="hidden",
        )
        self.btn_add.click(
            self.add_vlm,
            inputs=[
                self.add_name,
                self.add_provider,
                self.add_endpoint_url,
                self.add_model,
                self.add_api_key,
                self.add_ollama_server,
                self.add_ollama_model,
            ],
            outputs=[],
            show_progress="hidden",
        ).then(
            self.list_vlms,
            inputs=[],
            outputs=[self.vlm_list],
        ).then(
            lambda: (
                "",
                "azure_openai",
                "",
                "",
                "",
                gr.update(value=None, visible=False),
                gr.update(value="", visible=False),
            ),
            outputs=[
                self.add_name,
                self.add_provider,
                self.add_endpoint_url,
                self.add_model,
                self.add_api_key,
                self.add_ollama_server,
                self.add_ollama_model,
            ],
        )
        self.btn_save.click(
            self.save_vlm,
            inputs=[
                self.selected_vlm_name,
                self.edit_provider,
                self.edit_endpoint_url,
                self.edit_model,
                self.edit_api_key,
                self.edit_ollama_server,
                self.edit_ollama_model,
            ],
            outputs=[],
            show_progress="hidden",
        ).then(
            self.list_vlms,
            inputs=[],
            outputs=[self.vlm_list],
        )
        self.btn_delete.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=True),
            ),
            outputs=[
                self.btn_delete_confirm,
                self.btn_delete,
                self.btn_delete_cancel,
                self.btn_close_edit,
            ],
            show_progress="hidden",
        )
        self.btn_delete_confirm.click(
            self.delete_vlm,
            inputs=[self.selected_vlm_name],
            outputs=[self.selected_vlm_name],
            show_progress="hidden",
        ).then(
            lambda: gr.update(visible=False),
            outputs=[self._edit_panel],
        ).then(
            self.list_vlms,
            inputs=[],
            outputs=[self.vlm_list],
        )
        self.btn_delete_cancel.click(
            lambda: (
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ),
            outputs=[
                self.btn_delete_confirm,
                self.btn_delete,
                self.btn_delete_cancel,
                self.btn_close_edit,
            ],
            show_progress="hidden",
        )
        self.btn_close_edit.click(
            lambda: gr.update(visible=False),
            outputs=[self._edit_panel],
            show_progress="hidden",
        )

    def _spec_to_edit_ui(self, spec):
        s = spec or {}
        return (
            gr.update(visible=True, value=s.get("endpoint_url", "")),
            gr.update(visible=True, value=s.get("model", "")),
            gr.update(visible=True, value=s.get("api_key", "")),
            gr.update(
                visible=True,
                choices=[c[1] for c in ollama_servers_manager.options_for_dropdown()],
                value=s.get("ollama_server"),
            ),
        )

    def on_add_provider_change(self, provider):
        is_ollama = provider == "ollama"
        return (
            gr.update(visible=not is_ollama),
            gr.update(visible=not is_ollama),
            gr.update(visible=not is_ollama),
            gr.update(visible=is_ollama),
            gr.update(visible=is_ollama),
        )

    def on_edit_provider_change(self, provider):
        is_ollama = provider == "ollama"
        return (
            gr.update(visible=not is_ollama),
            gr.update(visible=not is_ollama),
            gr.update(visible=not is_ollama),
            gr.update(visible=is_ollama),
            gr.update(visible=is_ollama),
        )

    def on_select_vlm(self, df, ev: gr.SelectData):
        if not ev.selected or not df or df.empty:
            return (
                gr.update(visible=False),
                "",
                "azure_openai",
                "",
                "",
                "",
                gr.update(visible=False, value=None),
                "",
            )
        idx = ev.index[0]
        name = df.iloc[idx]["name"]
        v = vlms_manager.get(name)
        if not v:
            return (
                gr.update(visible=False),
                "",
                "azure_openai",
                "",
                "",
                "",
                gr.update(visible=False, value=None),
                "",
            )
        spec = v.get("spec") or {}
        provider = spec.get("provider", "azure_openai")
        is_ollama = provider == "ollama"
        return (
            gr.update(visible=True),
            name,
            provider,
            gr.update(visible=not is_ollama, value=spec.get("endpoint_url", "")),
            gr.update(visible=not is_ollama, value=spec.get("model", "")),
            gr.update(visible=not is_ollama, value=spec.get("api_key", "")),
            gr.update(
                visible=is_ollama,
                choices=[c[1] for c in ollama_servers_manager.options_for_dropdown()],
                value=spec.get("ollama_server"),
            ),
            gr.update(visible=is_ollama, value=spec.get("model", "llava")),
            name,
        )

    def _build_spec(
        self,
        provider,
        endpoint_url,
        model,
        api_key,
        ollama_server,
        ollama_model,
    ):
        if provider == "ollama":
            return {
                "provider": "ollama",
                "ollama_server": (ollama_server or "").strip(),
                "model": (ollama_model or "llava").strip(),
            }
        return {
            "provider": provider,
            "endpoint_url": (endpoint_url or "").strip(),
            "model": (model or "").strip(),
            "api_key": (api_key or "").strip() or None,
        }

    def add_vlm(
        self,
        name,
        provider,
        endpoint_url,
        model,
        api_key,
        ollama_server,
        ollama_model,
    ):
        name = (name or "").strip()
        if not name:
            raise gr.Error("Введите имя VLM")
        spec = self._build_spec(
            provider,
            endpoint_url,
            model,
            api_key,
            ollama_server,
            ollama_model,
        )
        if provider == "ollama":
            if not spec.get("ollama_server"):
                raise gr.Error("Выберите Ollama server")
            if not spec.get("model"):
                raise gr.Error("Введите имя модели Ollama (например llava)")
        try:
            vlms_manager.add(name=name, spec=spec)
            gr.Info(f"VLM «{name}» добавлен")
        except ValueError as e:
            raise gr.Error(str(e))

    def save_vlm(
        self,
        name,
        provider,
        endpoint_url,
        model,
        api_key,
        ollama_server,
        ollama_model,
    ):
        name = (name or "").strip()
        if not name:
            return
        spec = self._build_spec(
            provider,
            endpoint_url,
            model,
            api_key,
            ollama_server,
            ollama_model or "llava",
        )
        try:
            vlms_manager.update(name=name, spec=spec)
            gr.Info(f"VLM «{name}» сохранён")
        except ValueError as e:
            raise gr.Error(str(e))

    def delete_vlm(self, name):
        name = (name or "").strip()
        if not name:
            return ""
        try:
            vlms_manager.delete(name)
            gr.Info(f"VLM «{name}» удалён")
        except Exception as e:
            gr.Warning(str(e))
        return ""
