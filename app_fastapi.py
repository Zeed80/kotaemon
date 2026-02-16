"""Точка входа: FastAPI + Gradio, REST API для внешних агентов."""

import os
from pathlib import Path

# Применяем патч для httplib2/pyparsing совместимости ДО импорта других модулей
from ktem.utils.httplib2_patch import patch_httplib2_pyparsing  # noqa

patch_httplib2_pyparsing()

from theflow.settings import settings as flowsettings

KH_APP_DATA_DIR = getattr(flowsettings, "KH_APP_DATA_DIR", ".")
KH_GRADIO_SHARE = getattr(flowsettings, "KH_GRADIO_SHARE", False)
GRADIO_TEMP_DIR = os.getenv("GRADIO_TEMP_DIR", None)
if GRADIO_TEMP_DIR is None:
    GRADIO_TEMP_DIR = os.path.join(KH_APP_DATA_DIR, "gradio_tmp")
    os.environ["GRADIO_TEMP_DIR"] = GRADIO_TEMP_DIR


import gradio as gr
from fastapi import FastAPI

from ktem.api import api_router
from ktem.main import App

# Создаём Kotaemon App и Gradio demo
ktem_app = App()
demo = ktem_app.make()
demo.queue()

# FastAPI как основной app
fastapi_app = FastAPI(
    title="Kotaemon",
    description="RAG-based Question and Answering with REST API for external agents",
    version=getattr(ktem_app, "app_version", "1.0"),
)
fastapi_app.state.ktem_app = ktem_app
fastapi_app.include_router(api_router)

# Монтируем Gradio в корень
fastapi_app = gr.mount_gradio_app(
    fastapi_app,
    demo,
    path="/",
    allowed_paths=[
        str(Path(__file__).resolve().parent / "libs/ktem/ktem/assets"),
        GRADIO_TEMP_DIR,
    ],
)

app = fastapi_app
