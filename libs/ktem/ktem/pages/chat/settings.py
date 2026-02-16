"""Настройки чата — реэкспорт из pages.settings для совместимости."""

from ktem.pages.settings import load_chat_settings_values, save_chat_settings

__all__ = ["load_chat_settings_values", "save_chat_settings"]
