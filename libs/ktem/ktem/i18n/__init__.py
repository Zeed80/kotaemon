"""Локализация Kotaemon.

Поддерживаемые языки UI: en, ru, zh, de, fr, es, ja, uk.
Переключение «на лету» через выпадающий список в правом верхнем углу.
"""

from .loader import (
    SUPPORTED_UI_LANGS,
    get_all_keys,
    get_all_translations,
    get_text,
)

__all__ = ["get_text", "get_all_keys", "get_all_translations", "SUPPORTED_UI_LANGS"]
