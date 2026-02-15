"""Шифрование чувствительных данных (API-ключи, пароли) при хранении в БД и файлах.

Использует Fernet (AES-128-CBC). Ключ берётся из KH_ENCRYPTION_KEY в .env.
Если ключ не задан — хранение в открытом виде (обратная совместимость).

Префикс enc: помечает зашифрованные значения для миграции существующих данных.
"""

from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger(__name__)

_fernet = None

SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "qdrant_api_key",
        "password",
        "secret",
        "token",
        "credential",
    }
)


def _key_sensitive(key: str) -> bool:
    """Проверить, что ключ содержит чувствительные данные."""
    k = key.lower()
    for s in SENSITIVE_KEYS:
        if s in k or k.endswith("_key") or k.endswith("_secret"):
            return True
    return False


_SALT = b"kotaemon-secret-storage-v1"


def _get_fernet():
    """Получить Fernet instance; None если ключ не задан."""
    global _fernet
    if _fernet is not None:
        return _fernet
    try:
        from flowsettings_config import config

        raw = config("KH_ENCRYPTION_KEY", default="") or os.getenv("KH_ENCRYPTION_KEY", "")
    except Exception:
        raw = os.getenv("KH_ENCRYPTION_KEY", "")
    if not raw or not str(raw).strip():
        return None
    raw_bytes = str(raw).strip().encode("utf-8")
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_SALT,
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(raw_bytes))
        _fernet = Fernet(key)
        return _fernet
    except ImportError:
        logger.warning(
            "cryptography not installed; secrets will be stored in plain text. "
            "Install with: pip install cryptography"
        )
        return None
    except Exception as e:
        logger.warning("Invalid KH_ENCRYPTION_KEY: %s; secrets stored in plain text", e)
        return None


def encrypt_value(value: str | None) -> str | None:
    """Зашифровать строку. Возвращает 'enc:' + base64 ciphertext или исходную строку."""
    if value is None or value == "":
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        enc = f.encrypt(value.encode("utf-8"))
        return "enc:" + enc.decode("ascii")
    except Exception as e:
        logger.warning("Encryption failed: %s", e)
        return value


def decrypt_value(value: str | None) -> str | None:
    """Расшифровать строку. Если значение с префиксом enc: — расшифровать, иначе вернуть как есть."""
    if value is None or value == "":
        return value
    if not isinstance(value, str) or not value.startswith("enc:"):
        return value
    f = _get_fernet()
    if f is None:
        return value[4:] if len(value) > 4 else value
    try:
        dec = f.decrypt(value[4:].encode("ascii"))
        return dec.decode("utf-8")
    except Exception as e:
        logger.warning("Decryption failed: %s", e)
        return value


def process_dict_for_save(d: dict, prefix: str = "") -> dict:
    """Зашифровать чувствительные поля в словаре (in-place, возвращает d)."""
    for k, v in list(d.items()):
        full_key = f"{prefix}{k}" if prefix else k
        if isinstance(v, dict):
            process_dict_for_save(v, f"{full_key}.")
        elif isinstance(v, str) and _key_sensitive(full_key) and not v.startswith("enc:"):
            d[k] = encrypt_value(v)
    return d


def process_dict_for_load(d: dict, prefix: str = "") -> dict:
    """Расшифровать чувствительные поля в словаре (in-place, возвращает d)."""
    for k, v in list(d.items()):
        full_key = f"{prefix}{k}" if prefix else k
        if isinstance(v, dict):
            process_dict_for_load(v, f"{full_key}.")
        elif isinstance(v, str) and _key_sensitive(full_key):
            d[k] = decrypt_value(v)
    return d
