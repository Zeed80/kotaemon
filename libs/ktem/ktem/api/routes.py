"""REST API v1: upload, jobs, query."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from flowsettings_config import config

router = APIRouter(prefix="/api/v1", tags=["api"])

X_API_KEY = APIKeyHeader(name="X-API-Key", auto_error=False)
Bearer = HTTPBearer(auto_error=False)


def _get_api_key() -> str | None:
    return config("API_SECRET_KEY", default="") or os.getenv("API_SECRET_KEY", "")


async def _verify_api_key(
    request: Request,
    x_api_key: str | None = Depends(X_API_KEY),
    credentials: HTTPAuthorizationCredentials | None = Depends(Bearer),
) -> str | None:
    """Проверка аутентификации. Если API_SECRET_KEY пуст — доступ без токена."""
    api_key = _get_api_key()
    if not api_key:
        return "default"
    token = x_api_key or (credentials.parameter if credentials else None)
    if token and token == api_key:
        return "default"
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


# --- Schemas ---


class UploadResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str | None
    error: str | None
    result: dict[int, list[str | None]] | None


class QueryRequest(BaseModel):
    question: str
    file_ids: list[str] | None = None
    index_ids: list[int] | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: str


# --- Routes ---


@router.post("/upload", response_model=UploadResponse)
async def api_upload(
    request: Request,
    files: list[UploadFile] = File(default=[]),
    target_indices: str = Form(default=""),
    _: str | None = Depends(_verify_api_key),
):
    """Загрузить файлы и поставить в очередь индексации."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    app = request.app.state.ktem_app
    target_ids: list[int] = []
    if target_indices:
        for part in target_indices.split(","):
            part = part.strip()
            if part.isdigit():
                target_ids.append(int(part))
    if not target_ids:
        target_ids = [idx.id for idx in app.index_manager.indices]

    file_paths = []
    tmp_dir = tempfile.mkdtemp()
    try:
        for f in files:
            path = Path(tmp_dir) / (f.filename or str(uuid.uuid4()))
            content = await f.read()
            path.write_bytes(content)
            file_paths.append(str(path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save files: {e}") from e

    if not file_paths:
        raise HTTPException(status_code=400, detail="No valid files")

    app = request.app.state.ktem_app
    settings_dict = dict(app.default_settings.flatten())
    from ktem.pages.settings import get_user_settings

    settings_merged = get_user_settings("default", settings_dict)
    from ktem.orchestration.queue import get_indexing_queue

    queue = get_indexing_queue(app)
    queue.set_app(app)
    paths: list[str | Path] = [Path(p) for p in file_paths]
    job_id = queue.enqueue(
        file_paths=paths,
        target_indices=target_ids,
        user_id="default",
        settings=settings_merged,
        reindex=False,
        ingestion_id=uuid.uuid4().hex,
    )
    return UploadResponse(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def api_job_status(
    job_id: str,
    request: Request,
    _: str | None = Depends(_verify_api_key),
):
    """Получить статус задачи индексации."""
    app = request.app.state.ktem_app
    from ktem.orchestration.queue import get_indexing_queue

    queue = get_indexing_queue(app)
    job = queue.get_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        message=job.message or None,
        error=job.error,
        result=job.result,
    )


def _build_selecteds(
    app: Any,
    index_ids: list[int] | None,
    file_ids: list[str] | None,
    user_id: str = "default",
) -> list[Any]:
    """Построить selecteds для create_pipeline из index_ids и file_ids."""
    selecteds: list[Any] = []
    indices = app.index_manager.indices
    first_file_idx = 0
    for idx, index in enumerate(indices):
        if index_ids and index.id not in index_ids:
            mode, selected = "disabled", []
        elif file_ids and idx == first_file_idx:
            mode, selected = "select", file_ids
        else:
            mode, selected = "all", []
        selecteds.extend([mode, selected, user_id])
    return selecteds


@router.post("/query", response_model=QueryResponse)
async def api_query(
    body: QueryRequest,
    request: Request,
    _: str | None = Depends(_verify_api_key),
):
    """Запрос к RAG: вопрос, опционально file_ids и index_ids."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question is required")

    app = request.app.state.ktem_app
    chat_page = app.chat_page
    settings_dict = dict(app.default_settings.flatten())
    from ktem.pages.settings import get_user_settings

    settings = get_user_settings("default", settings_dict)
    user_id = "default"

    from ktem.pages.chat import DEFAULT_SETTING

    selecteds = _build_selecteds(
        app,
        body.index_ids,
        body.file_ids,
        user_id,
    )

    chat_state = {"app": {"regen": False}}
    pipeline, reasoning_state = chat_page.create_pipeline(
        settings,
        DEFAULT_SETTING,
        DEFAULT_SETTING,
        DEFAULT_SETTING,
        DEFAULT_SETTING,
        DEFAULT_SETTING,
        chat_state,
        None,
        user_id,
        *selecteds,
    )

    text = ""
    refs = ""
    chat_history: list[tuple[str, str | None]] = []
    conversation_id = None

    for response in pipeline.stream(
        body.question,
        conversation_id,
        chat_history,
    ):
        if not hasattr(response, "channel"):
            continue
        if response.channel == "chat" and response.content:
            text += response.content
        elif response.channel == "info" and response.content:
            refs += response.content

    return QueryResponse(answer=text or "(No answer)", sources=refs or "")
