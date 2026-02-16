"""UI вкладки «VLMs» в Resources: список, добавление, редактирование, удаление."""

import gradio as gr
import pandas as pd

from ktem.app import BasePage
from ktem.ollama_servers import ollama_servers_manager
from ktem.utils.ollama import get_ollama_models, pull_ollama_model
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
                    info="Выберите провайдера для VLM модели",
                )

                # Azure OpenAI / OpenAI секция
                with gr.Column(visible=True) as self._edit_azure_openai_section:
                    gr.Markdown("### Azure OpenAI / OpenAI")
                    self.edit_endpoint_url = gr.Textbox(
                        label="Endpoint URL",
                        info="URL chat/completions (Azure/OpenAI)",
                        placeholder="https://.../openai/deployments/.../chat/completions?api-version=...",
                    )
                    self.edit_model = gr.Textbox(
                        label="Модель",
                        info="Имя модели (например: gpt-4o, gpt-4o-mini)",
                        placeholder="gpt-4o",
                    )
                    self.edit_api_key = gr.Textbox(
                        label="API key (optional)",
                        type="password",
                        info="API ключ для доступа к сервису (опционально)",
                    )

                # Ollama секция
                with gr.Column(visible=False) as self._edit_ollama_section:
                    gr.Markdown("### Ollama")
                    self.edit_ollama_server = gr.Dropdown(
                        label="Ollama server",
                        choices=[],
                        value=None,
                        info="Выберите зарегистрированный сервер Ollama (добавьте в вкладке Ollama servers)",
                        allow_custom_value=False,
                        interactive=True,
                    )
                    gr.Markdown("### Model")
                    with gr.Row():
                        self.edit_ollama_model = gr.Dropdown(
                            label="Доступные модели Ollama",
                            choices=[],
                            value=None,
                            allow_custom_value=True,
                            info="Выберите модель из выбранного сервера",
                            interactive=True,
                        )
                        self.btn_refresh_edit_models = gr.Button(
                            "🔄 Refresh", scale=0, min_width=100
                        )
                    self.edit_ollama_model_input = gr.Textbox(
                        label="Или введите имя модели вручную",
                        info="Введите имя модели если её нет в списке выше",
                        placeholder="e.g., llava",
                    )
                    with gr.Row():
                        self.btn_pull_edit_model = gr.Button(
                            "⬇️ Pull Model", variant="secondary"
                        )
                        self.edit_ollama_pull_progress = gr.HTML(
                            visible=False, value=""
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
                info="Выберите провайдера для VLM модели",
            )

            # Azure OpenAI / OpenAI секция
            with gr.Column(visible=True) as self._add_azure_openai_section:
                gr.Markdown("### Azure OpenAI / OpenAI")
                self.add_endpoint_url = gr.Textbox(
                    label="Endpoint URL",
                    info="URL chat/completions (Azure/OpenAI)",
                    placeholder="https://.../openai/deployments/.../chat/completions?api-version=...",
                )
                self.add_model = gr.Textbox(
                    label="Модель",
                    info="Имя модели (например: gpt-4o, gpt-4o-mini)",
                    placeholder="gpt-4o",
                )
                self.add_api_key = gr.Textbox(
                    label="API key (optional)",
                    type="password",
                    info="API ключ для доступа к сервису (опционально)",
                )

            # Ollama секция
            with gr.Column(visible=False) as self._add_ollama_section:
                gr.Markdown("### Ollama")
                self.add_ollama_server = gr.Dropdown(
                    label="Ollama server",
                    choices=[],
                    value=None,
                    info="Выберите зарегистрированный сервер Ollama (добавьте в вкладке Ollama servers)",
                    allow_custom_value=False,
                    interactive=True,
                )
                gr.Markdown("### Model")
                with gr.Row():
                    self.add_ollama_model = gr.Dropdown(
                        label="Доступные модели Ollama",
                        choices=[],
                        value=None,
                        allow_custom_value=True,
                        info="Выберите модель из выбранного сервера",
                        interactive=True,
                    )
                    self.btn_refresh_add_models = gr.Button(
                        "🔄 Refresh", scale=0, min_width=100
                    )
                self.add_ollama_model_input = gr.Textbox(
                    label="Или введите имя модели вручную",
                    info="Введите имя модели если её нет в списке выше",
                    placeholder="e.g., llava",
                )
                with gr.Row():
                    self.btn_pull_add_model = gr.Button(
                        "⬇️ Pull Model", variant="secondary"
                    )
                    self.add_ollama_pull_progress = gr.HTML(visible=False, value="")

            self.btn_add = gr.Button("Добавить VLM", variant="primary")

    def _on_app_created(self):
        self._app.app.load(
            self.list_vlms,
            inputs=[],
            outputs=[self.vlm_list],
            show_progress="hidden",
        )
        server_choices = [c[1] for c in ollama_servers_manager.options_for_dropdown()]
        self._app.app.load(
            lambda: gr.update(choices=server_choices),
            outputs=[self.add_ollama_server],
            show_progress="hidden",
        )
        self._app.app.load(
            lambda: gr.update(choices=server_choices),
            outputs=[self.edit_ollama_server],
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
                self._edit_azure_openai_section,
                self._edit_ollama_section,
                self.edit_endpoint_url,
                self.edit_model,
                self.edit_api_key,
                self.edit_ollama_server,
                self.edit_ollama_model,
                self.btn_refresh_edit_models,
                self.edit_ollama_model_input,
                self.btn_pull_edit_model,
                self.selected_vlm_name,
            ],
            show_progress="hidden",
        )
        self.add_provider.change(
            self.on_add_provider_change,
            inputs=[self.add_provider],
            outputs=[
                self._add_azure_openai_section,
                self._add_ollama_section,
                self.add_endpoint_url,
                self.add_model,
                self.add_api_key,
                self.add_ollama_server,
                self.add_ollama_model,
                self.btn_refresh_add_models,
                self.add_ollama_model_input,
                self.btn_pull_add_model,
            ],
            show_progress="hidden",
        )
        self.edit_provider.change(
            self.on_edit_provider_change,
            inputs=[self.edit_provider],
            outputs=[
                self._edit_azure_openai_section,
                self._edit_ollama_section,
                self.edit_endpoint_url,
                self.edit_model,
                self.edit_api_key,
                self.edit_ollama_server,
                self.edit_ollama_model,
                self.btn_refresh_edit_models,
                self.edit_ollama_model_input,
                self.btn_pull_edit_model,
            ],
            show_progress="hidden",
        )
        self.add_ollama_server.change(
            self.on_add_ollama_server_selected,
            inputs=[self.add_ollama_server],
            outputs=[self.add_ollama_model],
            show_progress="hidden",
        )
        self.edit_ollama_server.change(
            self.on_edit_ollama_server_selected,
            inputs=[self.edit_ollama_server],
            outputs=[self.edit_ollama_model],
            show_progress="hidden",
        )
        self.btn_refresh_add_models.click(
            self.refresh_ollama_models,
            inputs=[self.add_ollama_server],
            outputs=[self.add_ollama_model],
            show_progress="hidden",
        )
        self.btn_refresh_edit_models.click(
            self.refresh_ollama_models,
            inputs=[self.edit_ollama_server],
            outputs=[self.edit_ollama_model],
            show_progress="hidden",
        )
        self.btn_pull_add_model.click(
            self.pull_ollama_model_ui,
            inputs=[self.add_ollama_server, self.add_ollama_model_input],
            outputs=[self.add_ollama_pull_progress, self.add_ollama_model],
            show_progress="hidden",
        )
        self.btn_pull_edit_model.click(
            self.pull_ollama_model_ui,
            inputs=[self.edit_ollama_server, self.edit_ollama_model_input],
            outputs=[self.edit_ollama_pull_progress, self.edit_ollama_model],
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
                self.add_ollama_model_input,
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
                gr.update(visible=True),
                gr.update(visible=False),
                "",
                "",
                "",
                gr.update(value=None, visible=False),
                gr.update(choices=[], value=None, visible=False),
                gr.update(visible=False),
                gr.update(value="", visible=False),
                gr.update(visible=False),
            ),
            outputs=[
                self.add_name,
                self.add_provider,
                self._add_azure_openai_section,
                self._add_ollama_section,
                self.add_endpoint_url,
                self.add_model,
                self.add_api_key,
                self.add_ollama_server,
                self.add_ollama_model,
                self.btn_refresh_add_models,
                self.add_ollama_model_input,
                self.btn_pull_add_model,
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
                self.edit_ollama_model_input,
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
        server_choices = [c[1] for c in ollama_servers_manager.options_for_dropdown()]
        server_value = server_choices[0] if server_choices else None
        model_choices = []
        if is_ollama and server_value:
            models = get_ollama_models(
                ollama_servers_manager.get(server_value)["base_url"]
                if ollama_servers_manager.get(server_value)
                else None
            )
            model_choices = [m["name"] for m in models] if models else []
        return (
            gr.update(visible=not is_ollama),  # _add_azure_openai_section
            gr.update(visible=is_ollama),  # _add_ollama_section
            gr.update(visible=not is_ollama),  # add_endpoint_url
            gr.update(visible=not is_ollama),  # add_model
            gr.update(visible=not is_ollama),  # add_api_key
            gr.update(
                visible=is_ollama, choices=server_choices, value=server_value
            ),  # add_ollama_server
            gr.update(
                visible=is_ollama,
                choices=model_choices,
                value=model_choices[0] if model_choices else None,
            ),  # add_ollama_model
            gr.update(visible=is_ollama),  # btn_refresh_add_models
            gr.update(visible=is_ollama),  # add_ollama_model_input
            gr.update(visible=is_ollama),  # btn_pull_add_model
        )

    def on_edit_provider_change(self, provider):
        is_ollama = provider == "ollama"
        server_choices = [c[1] for c in ollama_servers_manager.options_for_dropdown()]
        return (
            gr.update(visible=not is_ollama),  # _edit_azure_openai_section
            gr.update(visible=is_ollama),  # _edit_ollama_section
            gr.update(visible=not is_ollama),  # edit_endpoint_url
            gr.update(visible=not is_ollama),  # edit_model
            gr.update(visible=not is_ollama),  # edit_api_key
            gr.update(visible=is_ollama, choices=server_choices),  # edit_ollama_server
            gr.update(visible=is_ollama, choices=[]),  # edit_ollama_model
            gr.update(visible=is_ollama),  # btn_refresh_edit_models
            gr.update(visible=is_ollama),  # edit_ollama_model_input
            gr.update(visible=is_ollama),  # btn_pull_edit_model
        )

    def on_select_vlm(self, df, ev: gr.SelectData):
        if not ev.selected or df is None or df.empty:
            return (
                gr.update(visible=False),
                "",
                "azure_openai",
                gr.update(visible=True),
                gr.update(visible=False),
                "",
                "",
                "",
                gr.update(visible=False, value=None),
                gr.update(visible=False, choices=[], value=None),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
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
                gr.update(visible=True),
                gr.update(visible=False),
                "",
                "",
                "",
                gr.update(visible=False, value=None),
                gr.update(visible=False, choices=[], value=None),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                "",
            )
        spec = v.get("spec") or {}
        provider = spec.get("provider", "azure_openai")
        is_ollama = provider == "ollama"
        model_value = spec.get("model", "llava")
        model_choices = []
        if is_ollama:
            server_name = spec.get("ollama_server")
            if server_name:
                s = ollama_servers_manager.get(server_name)
                if s:
                    models = get_ollama_models(s["base_url"])
                    model_choices = [m["name"] for m in models] if models else []
        return (
            gr.update(visible=True),
            name,
            provider,
            gr.update(visible=not is_ollama),  # _edit_azure_openai_section
            gr.update(visible=is_ollama),  # _edit_ollama_section
            gr.update(visible=not is_ollama, value=spec.get("endpoint_url", "")),
            gr.update(visible=not is_ollama, value=spec.get("model", "")),
            gr.update(visible=not is_ollama, value=spec.get("api_key", "")),
            gr.update(
                visible=is_ollama,
                choices=[c[1] for c in ollama_servers_manager.options_for_dropdown()],
                value=spec.get("ollama_server"),
            ),
            gr.update(
                visible=is_ollama,
                choices=model_choices,
                value=model_value if model_value in model_choices else None,
            ),
            gr.update(visible=is_ollama),
            gr.update(
                visible=is_ollama,
                value=model_value if model_value not in model_choices else "",
            ),
            gr.update(visible=is_ollama),
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
        ollama_model_input=None,
    ):
        if provider == "ollama":
            # Использовать значение из dropdown или из input поля
            model_value = (ollama_model or "").strip() or (
                ollama_model_input or ""
            ).strip()
            return {
                "provider": "ollama",
                "ollama_server": (ollama_server or "").strip(),
                "model": model_value or "llava",
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
        ollama_model_input,
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
            ollama_model_input,
        )
        if provider == "ollama":
            if not spec.get("ollama_server"):
                raise gr.Error("Выберите Ollama server")
            model_value = spec.get("model", "").strip()
            if not model_value:
                raise gr.Error(
                    "Выберите или введите имя модели Ollama (например llava)"
                )
        try:
            vlms_manager.add(name=name, spec=spec)
            gr.Info(f"VLM «{name}» добавлен", duration=1)
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
        ollama_model_input,
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
            ollama_model,
            ollama_model_input,
        )
        if provider == "ollama" and not spec.get("model"):
            spec["model"] = "llava"
        try:
            vlms_manager.update(name=name, spec=spec)
            gr.Info(f"VLM «{name}» сохранён", duration=1)
        except ValueError as e:
            raise gr.Error(str(e))

    def refresh_ollama_models(self, server_name=None):
        """Обновить список моделей из Ollama (с выбранного сервера или по умолчанию)."""
        base_url = None
        if server_name:
            s = ollama_servers_manager.get(server_name)
            if s:
                base_url = s["base_url"]
        try:
            models = get_ollama_models(base_url)
            if models:
                choices = [model["name"] for model in models]
                return gr.update(choices=choices, value=choices[0] if choices else None)
            return gr.update(choices=[], value=None)
        except Exception as e:
            gr.Warning(f"Не удалось получить список моделей Ollama: {e}", duration=1)
            return gr.update(choices=[], value=None)

    def on_add_ollama_server_selected(self, server_name):
        """При выборе сервера Ollama в форме Add обновить список моделей."""
        if not server_name:
            return gr.update(choices=[], value=None)
        return self.refresh_ollama_models(server_name)

    def on_edit_ollama_server_selected(self, server_name):
        """При выборе сервера Ollama в форме Edit обновить список моделей."""
        if not server_name:
            return gr.update(choices=[], value=None)
        return self.refresh_ollama_models(server_name)

    def pull_ollama_model_ui(self, server_name: str, model_name: str):
        """Загрузить модель из Ollama с отображением прогресса."""
        if not model_name:
            gr.Warning("Введите имя модели для загрузки", duration=1)
            yield gr.update(visible=False, value=""), gr.update()
            return

        base_url = None
        if server_name:
            s = ollama_servers_manager.get(server_name)
            if s:
                base_url = s["base_url"]

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
                    # Обновить список моделей
                    models = get_ollama_models(base_url)
                    choices = [m["name"] for m in models] if models else []
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

    def delete_vlm(self, name):
        name = (name or "").strip()
        if not name:
            return ""
        try:
            vlms_manager.delete(name)
            gr.Info(f"VLM «{name}» удалён", duration=1)
        except Exception as e:
            gr.Warning(str(e), duration=1)
        return ""
