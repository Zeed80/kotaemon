"""VLM (vision models): БД, менеджер, get_endpoint."""

from .db import VLMTable
from .manager import VLMManager, vlms_manager

__all__ = [
    "VLMTable",
    "VLMManager",
    "vlms_manager",
]
