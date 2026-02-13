"""UI вкладки «Ollama servers» в Resources: список, добавление, редактирование, удаление."""

import gradio as gr
import pandas as pd
from ktem.app import BasePage

from ktem.ollama_servers import ollama_servers_manager


def _status_icon(ok: bool) -> str:
    return "🟢" if ok else "🔴"


class OllamaServersManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            with gr.Row():
                self.server_list = gr.DataFrame(
                    headers=["name", "base_url", "num_ctx", "status"],
                    interactive=False,
                    label="Серверы Ollama",
                )
                self.btn_refresh_status = gr.Button(
                    "Проверить доступность",
                    size="sm",
                )
            with gr.Column(visible=False) as self._edit_panel:
                self.edit_name = gr.Textbox(label="Имя", interactive=False)
                self.edit_base_url = gr.Textbox(label="Ollama API URL")
                self.edit_num_ctx = gr.Number(
                    label="Макс. контекст (num_ctx)",
                    value=8192,
                    precision=0,
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
                self.selected_server_name = gr.Textbox(value="", visible=False)

        with gr.Tab(label="Add"):
            self.add_name = gr.Textbox(
                label="Имя",
                info="Уникальное имя сервера (например: local, dev)",
            )
            self.add_base_url = gr.Textbox(
                label="Ollama API URL",
                info="Например: http://localhost:11434/v1/",
                placeholder="http://localhost:11434/v1/",
            )
            self.add_num_ctx = gr.Number(
                label="Макс. контекст (num_ctx)",
                value=8192,
                precision=0,
                info="Размер контекстного окна по умолчанию для моделей на этом сервере.",
            )
            self.btn_add = gr.Button("Добавить сервер", variant="primary")

    def _on_app_created(self):
        self._app.app.load(
            self.list_servers,
            inputs=[],
            outputs=[self.server_list],
            show_progress="hidden",
        )

    def list_servers(self, with_status: bool = False):
        """Таблица серверов; при with_status — добавить колонку status (проверка доступности)."""
        rows = ollama_servers_manager.list()
        if not rows:
            return pd.DataFrame(
                columns=["name", "base_url", "num_ctx", "status"],
            )
        if with_status:
            data = []
            for s in rows:
                ok, _ = ollama_servers_manager.check_available(s["name"])
                data.append({
                    "name": s["name"],
                    "base_url": s["base_url"],
                    "num_ctx": s["num_ctx"],
                    "status": _status_icon(ok),
                })
        else:
            data = [
                {
                    "name": s["name"],
                    "base_url": s["base_url"],
                    "num_ctx": s["num_ctx"],
                    "status": "—",
                }
                for s in rows
            ]
        return pd.DataFrame(data)

    def list_servers_with_status(self):
        return self.list_servers(with_status=True)

    def on_register_events(self):
        self.btn_refresh_status.click(
            self.list_servers_with_status,
            inputs=[],
            outputs=[self.server_list],
            show_progress="hidden",
        )
        self.server_list.select(
            self.on_select_server,
            inputs=[self.server_list],
            outputs=[
                self._edit_panel,
                self.edit_name,
                self.edit_base_url,
                self.edit_num_ctx,
                self.selected_server_name,
            ],
            show_progress="hidden",
        )
        self.btn_add.click(
            self.add_server,
            inputs=[self.add_name, self.add_base_url, self.add_num_ctx],
            outputs=[],
            show_progress="hidden",
        ).then(
            self.list_servers,
            inputs=[],
            outputs=[self.server_list],
        ).then(
            lambda: ("", "", 8192),
            outputs=[self.add_name, self.add_base_url, self.add_num_ctx],
        )
        self.btn_save.click(
            self.save_server,
            inputs=[
                self.selected_server_name,
                self.edit_base_url,
                self.edit_num_ctx,
            ],
            outputs=[],
            show_progress="hidden",
        ).then(
            self.list_servers,
            inputs=[],
            outputs=[self.server_list],
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
            self.delete_server,
            inputs=[self.selected_server_name],
            outputs=[self.selected_server_name],
            show_progress="hidden",
        ).then(
            lambda: (
                gr.update(visible=False),
                "",
                "",
                8192,
                "",
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
            ),
            outputs=[
                self._edit_panel,
                self.edit_name,
                self.edit_base_url,
                self.edit_num_ctx,
                self.selected_server_name,
                self.btn_delete_confirm,
                self.btn_delete,
                self.btn_delete_cancel,
            ],
        ).then(
            self.list_servers,
            inputs=[],
            outputs=[self.server_list],
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
            lambda: (
                gr.update(visible=False),
                "",
                "",
                8192,
                "",
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
            ),
            outputs=[
                self._edit_panel,
                self.edit_name,
                self.edit_base_url,
                self.edit_num_ctx,
                self.selected_server_name,
                self.btn_delete_confirm,
                self.btn_delete,
                self.btn_delete_cancel,
            ],
            show_progress="hidden",
        )

    def on_select_server(self, df, ev: gr.SelectData):
        if not ev.selected or not df or df.empty:
            return (
                gr.update(visible=False),
                "",
                "",
                8192,
                "",
            )
        idx = ev.index[0]
        name = df.iloc[idx]["name"]
        server = ollama_servers_manager.get(name)
        if not server:
            return (
                gr.update(visible=False),
                "",
                "",
                8192,
                "",
            )
        return (
            gr.update(visible=True),
            server["name"],
            server["base_url"],
            server["num_ctx"],
            server["name"],
        )

    def add_server(self, name, base_url, num_ctx):
        name = (name or "").strip()
        base_url = (base_url or "").strip()
        if not name:
            raise gr.Error("Введите имя сервера")
        if not base_url:
            raise gr.Error("Введите Ollama API URL")
        num_ctx = int(num_ctx) if num_ctx is not None else 8192
        try:
            ollama_servers_manager.add(name=name, base_url=base_url, num_ctx=num_ctx)
            gr.Info(f"Сервер «{name}» добавлен")
        except ValueError as e:
            raise gr.Error(str(e))

    def save_server(self, name, base_url, num_ctx):
        name = (name or "").strip()
        base_url = (base_url or "").strip()
        if not name:
            return
        num_ctx = int(num_ctx) if num_ctx is not None else 8192
        try:
            ollama_servers_manager.update(name=name, base_url=base_url, num_ctx=num_ctx)
            gr.Info(f"Сервер «{name}» сохранён")
        except ValueError as e:
            raise gr.Error(str(e))

    def delete_server(self, name):
        name = (name or "").strip()
        if not name:
            return ""
        try:
            ollama_servers_manager.delete(name)
            gr.Info(f"Сервер «{name}» удалён")
        except Exception as e:
            gr.Warning(str(e))
        return ""
