"""Очередь задач индексации с фоновым воркером.

Минимальная зависимость: queue.Queue + threading.Thread.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Empty, Queue

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    INDEXING = "indexing"
    DONE = "done"
    FAILED = "failed"


# Макс. строк лога в задаче (чтобы не раздувать память)
JOB_DEBUG_LOG_MAX_LINES = 300


@dataclass
class JobInfo:
    """Информация о задаче индексации."""

    job_id: str
    file_paths: list[str | Path]
    target_indices: list[int]
    user_id: str
    settings: dict
    reindex: bool
    ingestion_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    result: dict[int, list[str | None]] = field(default_factory=dict)
    error: str | None = None
    callbacks: list[Callable[[JobInfo], None]] = field(default_factory=list, repr=False)
    debug_logs: list[str] = field(default_factory=list, repr=False)


class IndexingJobQueue:
    """Очередь задач индексации с фоновым воркером."""

    def __init__(self, app=None):
        self._queue: Queue[JobInfo] = Queue()
        self._jobs: dict[str, JobInfo] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._app = app

    def set_app(self, app):
        """Установить ссылку на приложение (для доступа к index_manager)."""
        self._app = app

    def enqueue(
        self,
        file_paths: list[str | Path],
        target_indices: list[int],
        user_id: str,
        settings: dict,
        reindex: bool = False,
        ingestion_id: str | None = None,
        callbacks: list[Callable[[JobInfo], None]] | None = None,
    ) -> str:
        """
        Добавить задачу в очередь.

        Returns:
            job_id
        """
        job_id = uuid.uuid4().hex
        ingestion_id = ingestion_id or uuid.uuid4().hex
        job = JobInfo(
            job_id=job_id,
            file_paths=[Path(p) if isinstance(p, str) and not p.startswith("http") else p for p in file_paths],
            target_indices=target_indices,
            user_id=user_id,
            settings=dict(settings),
            reindex=reindex,
            ingestion_id=ingestion_id,
            status=JobStatus.QUEUED,
            callbacks=callbacks or [],
        )
        with self._lock:
            self._jobs[job_id] = job
        self._queue.put(job)
        logger.info("Enqueued job %s: %d files, indices %s", job_id, len(file_paths), target_indices)
        return job_id

    def get_status(self, job_id: str) -> JobInfo | None:
        """Получить статус задачи."""
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job: JobInfo) -> None:
        """Выполнить одну задачу индексации."""
        if not self._app:
            job.status = JobStatus.FAILED
            job.error = "App not initialized"
            return

        index_manager = getattr(self._app, "index_manager", None)
        if not index_manager:
            job.status = JobStatus.FAILED
            job.error = "Index manager not available"
            return

        job.status = JobStatus.INDEXING
        job.message = "Starting indexing..."
        total_indices = len(job.target_indices)
        index_results: dict[int, list[str | None]] = {}

        for idx, index_id in enumerate(job.target_indices):
            index_obj = None
            for i in index_manager.indices:
                if i.id == index_id:
                    index_obj = i
                    break
            if not index_obj:
                job.message = f"Index {index_id} not found"
                continue

            try:
                job.message = f"Indexing {index_obj.name}..."
                pipeline = index_obj.get_indexing_pipeline(job.settings, job.user_id)
                output_stream = pipeline.stream(
                    job.file_paths,
                    reindex=job.reindex,
                    ingestion_id=job.ingestion_id,
                )
                results: list[str | None] = []
                while True:
                    try:
                        doc = next(output_stream)
                    except StopIteration as e:
                        if e.value:
                            file_ids, _, _ = e.value
                            results = list(file_ids) if file_ids else []
                        break
                    if doc is None:
                        continue
                    if getattr(doc, "channel", None) == "debug":
                        line = getattr(doc, "text", None) or str(getattr(doc, "content", ""))
                        if line:
                            job.debug_logs.append(line)
                            if len(job.debug_logs) > JOB_DEBUG_LOG_MAX_LINES:
                                job.debug_logs = job.debug_logs[-JOB_DEBUG_LOG_MAX_LINES:]
                            job.message = line[:200] + ("..." if len(line) > 200 else "")
                index_results[index_id] = results
                job.progress = (idx + 1) / total_indices
                job.message = f"Indexed {index_obj.name}"
                logger.info("Job %s: finished index %s (%s)", job.job_id, index_id, index_obj.name)
            except Exception as e:
                logger.exception("Indexing failed for index %s: %s", index_id, e)
                job.error = str(e)
                index_results[index_id] = []

        job.result = index_results
        job.status = JobStatus.DONE
        job.progress = 1.0
        job.message = "Completed"

        for cb in job.callbacks:
            try:
                cb(job)
            except Exception as e:
                logger.warning("Job callback failed: %s", e)

    def _worker_loop(self) -> None:
        """Цикл воркера."""
        while not self._stop.is_set():
            try:
                job = self._queue.get(timeout=0.5)
                self._run_job(job)
            except Empty:
                continue
            except Exception as e:
                logger.exception("Worker error: %s", e)

    def start(self) -> None:
        """Запустить фоновый воркер."""
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        logger.info("Indexing job queue worker started")

    def stop(self) -> None:
        """Остановить воркер."""
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=5.0)
            self._worker = None


# Синглтон очереди (инициализируется при старте приложения)
_indexing_queue: IndexingJobQueue | None = None


def get_indexing_queue(app=None) -> IndexingJobQueue:
    """Получить глобальную очередь индексации."""
    global _indexing_queue
    if _indexing_queue is None:
        _indexing_queue = IndexingJobQueue(app)
        _indexing_queue.start()
    elif app and _indexing_queue._app is None:
        _indexing_queue.set_app(app)
    return _indexing_queue
