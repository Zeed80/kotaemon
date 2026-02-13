"""UI вкладки «Ollama servers» в Resources: список, добавление, редактирование, удаление."""

import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.utils.ollama import check_ollama_available

from ktem.ollama_servers import ollama_servers_manager


def _status_icon(ok: bool) -> str:
    return "🟢" if ok else "🔴"


def _ollama_status_html(ok: bool, message: str) -> str:
    """HTML индикатора доступности Ollama (зелёный/красный кружок)."""
    if ok:
        color, title = "#22c55e", "Ollama доступен"
    else:
        color = "#ef4444"
        title = {"timeout": "Таймаут", "unreachable": "Недоступен", "error": "Ошибка"}.get(
            message, "Недоступен"
        )
    return (
        f'<span title="{title}" style="'
        "display: inline-block; width: 14px; height: 14px; border-radius: 50%; "
        f"background: {color}; margin-left: 8px; vertical-align: middle;"
        '" aria-label="Ollama status"></span>'
    )


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
                gr.Markdown("### Основные параметры")
                self.edit_name = gr.Textbox(label="Имя", interactive=False)
                gr.Markdown("### Подключение")
                with gr.Row():
                    self.edit_base_url = gr.Textbox(
                        label="Ollama API URL",
                        info="Проверка выполняется на сервере Kotaemon. localhost — машина, где запущено приложение.",
                        placeholder="http://localhost:11434/v1/",
                        scale=4,
                    )
                    self.edit_status_html = gr.HTML(
                        value=_ollama_status_html(False, "unreachable"),
                        elem_classes=["ollama-status"],
                    )
                    self.btn_check_edit = gr.Button("Проверить", size="sm", min_width=80, scale=0)
                gr.Markdown("### Настройки модели")
                self.edit_num_ctx = gr.Number(
                    label="Макс. контекст (num_ctx)",
                    value=8192,
                    precision=0,
                    info="Размер контекстного окна по умолчанию для моделей на этом сервере.",
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
            gr.Markdown("### Основные параметры")
            self.add_name = gr.Textbox(
                label="Имя",
                info="Уникальное имя сервера (например: local, dev)",
                placeholder="local",
            )
            gr.Markdown("### Подключение")
            with gr.Row():
                self.add_base_url = gr.Textbox(
                    label="Ollama API URL",
                    info="Проверка выполняется на сервере Kotaemon. localhost — машина, где запущено приложение.",
                    placeholder="http://localhost:11434/v1/",
                    scale=4,
                )
                self.add_status_html = gr.HTML(
                    value=_ollama_status_html(False, "unreachable"),
                    elem_classes=["ollama-status"],
                )
                self.btn_check_add = gr.Button("Проверить", size="sm", min_width=80, scale=0)
            gr.Markdown("### Настройки модели")
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

    def _check_add_url_and_return_html(self, url):
        """Проверка доступности по URL (форма Add). Выполняется на бэкенде."""
        ok, msg = check_ollama_available(url)
        return _ollama_status_html(ok, msg)

    def _check_edit_url_and_return_html(self, url):
        """Проверка доступности по URL (форма Edit). Выполняется на бэкенде."""
        ok, msg = check_ollama_available(url)
        return _ollama_status_html(ok, msg)

    def on_register_events(self):
        self.btn_check_add.click(
            self._check_add_url_and_return_html,
            inputs=[self.add_base_url],
            outputs=[self.add_status_html],
            show_progress="hidden",
        )
        self.btn_check_edit.click(
            self._check_edit_url_and_return_html,
            inputs=[self.edit_base_url],
            outputs=[self.edit_status_html],
            show_progress="hidden",
        )
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
                self.edit_status_html,
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
            self.list_servers_with_status,
            inputs=[],
            outputs=[self.server_list],
        ).then(
            lambda: ("", "", 8192, _ollama_status_html(False, "unreachable")),
            outputs=[
                self.add_name,
                self.add_base_url,
                self.add_num_ctx,
                self.add_status_html,
            ],
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
                _ollama_status_html(False, "unreachable"),
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
                self.edit_status_html,
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
                _ollama_status_html(False, "unreachable"),
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
                self.edit_status_html,
                self.edit_num_ctx,
                self.selected_server_name,
                self.btn_delete_confirm,
                self.btn_delete,
                self.btn_delete_cancel,
            ],
            show_progress="hidden",
        )

    def on_select_server(self, df, ev: gr.SelectData):
        if not ev.selected or df is None or df.empty:
            return (
                gr.update(visible=False),
                "",
                "",
                _ollama_status_html(False, "unreachable"),
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
                _ollama_status_html(False, "unreachable"),
                8192,
                "",
            )
        ok, msg = ollama_servers_manager.check_available(name)
        return (
            gr.update(visible=True),
            server["name"],
            server["base_url"],
            _ollama_status_html(ok, msg),
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
