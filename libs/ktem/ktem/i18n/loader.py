"""Загрузка переводов из JSON."""

from __future__ import annotations

import json
from pathlib import Path

_CACHE: dict[str, dict[str, str]] = {}
_BASE_DIR = Path(__file__).parent / "translations"

SUPPORTED_UI_LANGS = [
    ("English", "en"),
    ("Русский", "ru"),
    ("中文", "zh"),
    ("Deutsch", "de"),
    ("Français", "fr"),
    ("Español", "es"),
    ("日本語", "ja"),
    ("Українська", "uk"),
    ("Português", "pt"),
]


def _load(lang: str) -> dict[str, str]:
    if lang not in _CACHE:
        path = _BASE_DIR / f"{lang}.json"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                _CACHE[lang] = json.load(f)
        else:
            _CACHE[lang] = {}
    return _CACHE[lang]


def get_text(lang: str, key: str, default: str | None = None) -> str:
    """Получить строку перевода по ключу.

    Args:
        lang: Код языка (en, ru, zh, ...)
        key: Ключ перевода (точечная нотация: tab.chat, btn.save)
        default: Значение по умолчанию при отсутствии перевода

    Returns:
        Переведённая строка или default или key
    """
    if not lang or lang == "default":
        lang = "en"
    data = _load(lang)
    val = data.get(key)
    if val is not None:
        return str(val)
    if lang != "en":
        en_data = _load("en")
        val = en_data.get(key)
        if val is not None:
            return str(val)
    return default if default is not None else key


def get_all_keys() -> list[str]:
    """Вернуть все ключи из английского словаря."""
    return list(_load("en").keys())


def get_all_translations() -> dict[str, dict[str, str]]:
    """Вернуть все переводы для всех поддерживаемых языков.

    Returns:
        Словарь {lang: {key: value}}, например {"en": {"tab.chat": "Chat"}, ...}
    """
    result = {}
    for _, lang_code in SUPPORTED_UI_LANGS:
        result[lang_code] = _load(lang_code).copy()
    return result
