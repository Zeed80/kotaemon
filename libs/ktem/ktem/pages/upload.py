"""Единая точка загрузки файлов с фоновой индексацией."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

import gradio as gr
from theflow.settings import settings as flowsettings

from flowsettings_config import config
from ktem.app import BasePage
from ktem.i18n import get_text
from ktem.orchestration.queue import JobStatus, get_indexing_queue

from .settings import get_user_settings

logger = logging.getLogger(__name__)

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)


class UnifiedUploadPage(BasePage):
    """Единая страница загрузки: один upload для нескольких индексов в фоне."""

    def __init__(self, app):
        super().__init__(app)
        self._job_id_state = gr.State(value=None)
        if not KH_DEMO_MODE:
            self.on_building_ui()

    def on_building_ui(self):
        with gr.Column():
            gr.Markdown("### Unified Upload")
            gr.Markdown(
                "Upload files once and index into multiple collections in the background."
            )

            self.files_input = gr.File(
                file_count="multiple",
                label="Files",
                type="filepath",
            )
            self.index_checkboxes = gr.CheckboxGroup(
                choices=[],
                value=[],
                label="Target indices",
                info="Select which indices to index into.",
            )
            self.reindex_check = gr.Checkbox(
                value=False,
                label="Force reindex",
            )
            self.upload_btn = gr.Button("Upload and Index", variant="primary")

            with gr.Accordion("Job status", open=True) as self.status_accordion:
                self.status_text = gr.Textbox(
                    label="Status (обновляется автоматически во время индексации)",
                    value="No active job",
                    interactive=False,
                    lines=22,
                    max_lines=40,
                )
                self.refresh_btn = gr.Button("Refresh status", variant="secondary")

    def on_register_events(self):
        if KH_DEMO_MODE:
            return

        def update_index_choices():
            choices = [
                (f"{idx.name} (id={idx.id})", idx.id)
                for idx in self._app.index_manager.indices
            ]
            return gr.update(choices=choices)

        self._app.app.load(
            fn=update_index_choices,
            outputs=[self.index_checkboxes],
        )

        def do_upload(files, selected_indices, reindex, settings, user_id):
            if not files:
                return "No files selected.", None
            if not selected_indices:
                return "Select at least one target index.", None

            file_paths = []
            for f in files:
                if isinstance(f, (str, Path)):
                    path = Path(f)
                elif hasattr(f, "name"):
                    path = Path(f.name) if f.name else Path(getattr(f, "path", str(f)))
                else:
                    path = Path(str(f))
                if path.exists():
                    file_paths.append(str(path))

            if not file_paths:
                return "No valid file paths.", None

            queue = get_indexing_queue(self._app)
            queue.set_app(self._app)
            settings_dict = dict(settings) if settings else self._app.default_settings.flatten()
            user_id_val = user_id or "default"
            settings_merged = get_user_settings(user_id_val, settings_dict)

            job_id = queue.enqueue(
                file_paths=file_paths,
                target_indices=selected_indices,
                user_id=user_id_val,
                settings=settings_merged,
                reindex=reindex,
                ingestion_id=uuid.uuid4().hex,
            )
            return f"Job {job_id} queued. {len(file_paths)} file(s), {len(selected_indices)} index(es).", job_id

        def refresh_status(job_id):
            if not job_id:
                return "No active job"
            queue = get_indexing_queue(self._app)
            job = queue.get_status(job_id)
            if not job:
                return f"Job {job_id} not found."
            status = job.status.value
            progress = job.progress * 100
            msg = job.message or ""
            err = job.error or ""
            total_indices = len(job.target_indices)
            current = int(progress * total_indices / 100) if total_indices else 0
            stage = f"Index {current + 1}/{total_indices}" if total_indices else ""
            lines = [
                f"Job: {job_id}",
                f"Status: {status}",
                f"Progress: {progress:.0f}%",
                stage and f"Stage: {stage}",
                msg,
            ]
            lines = [x for x in lines if x]
            if err:
                lines.append(f"Error: {err}")
            if job.result:
                lines.append(f"Result: {job.result}")
            if getattr(job, "debug_logs", None):
                lines.append("\n--- Log (last lines) ---")
                lines.extend(job.debug_logs[-80:])
            return "\n".join(lines)

        def _chain_refresh_file_indices(chain):
            """Привязать обновление списков файлов индексов к цепочке."""
            events = getattr(self._app, "_events", {}) or {}
            for idx in self._app.index_manager.indices:
                event_name = f"onFileIndex{idx.id}Changed"
                if event_name not in events:
                    continue
                for event_def in self._app.get_event(event_name):
                    chain = chain.then(**event_def)
            return chain

        upload_chain = (
            self.upload_btn.click(
                fn=do_upload,
                inputs=[
                    self.files_input,
                    self.index_checkboxes,
                    self.reindex_check,
                    self._app.settings_state,
                    self._app.user_id,
                ],
                outputs=[self.status_text, self._job_id_state],
            )
            .then(
                fn=refresh_status,
                inputs=[self._job_id_state],
                outputs=[self.status_text],
            )
        )
        _chain_refresh_file_indices(upload_chain)

        refresh_chain = self.refresh_btn.click(
            fn=refresh_status,
            inputs=[self._job_id_state],
            outputs=[self.status_text],
        )
        _chain_refresh_file_indices(refresh_chain)

        # Автообновление статуса каждые 2 с — видно этап и лог во время индексации
        self._status_timer = gr.Timer(value=2)
        self._status_timer.tick(
            fn=refresh_status,
            inputs=[self._job_id_state],
            outputs=[self.status_text],
        )
