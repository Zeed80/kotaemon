from pathlib import Path

from kotaemon.base import Document

from .base import BaseReader

# Кодировки для fallback (русские и др.): utf-8, Windows-1251, KOI8-R
_FALLBACK_ENCODINGS = ("utf-8", "utf-8-sig", "cp1251", "windows-1251", "koi8-r", "latin-1")


def _read_text_with_fallback(file_path: Path) -> str:
    """Читает файл, пробуя кодировки по порядку (поддержка русской cp1251 и др.)."""
    last_error: Exception | None = None
    for enc in _FALLBACK_ENCODINGS:
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError) as e:
            last_error = e
            continue
    raise last_error or RuntimeError(f"Could not decode {file_path}")


class TxtReader(BaseReader):
    def run(
        self, file_path: str | Path, extra_info: dict | None = None, **kwargs
    ) -> list[Document]:
        return self.load_data(Path(file_path), extra_info=extra_info, **kwargs)

    def load_data(
        self, file_path: Path, extra_info: dict | None = None, **kwargs
    ) -> list[Document]:
        text = _read_text_with_fallback(file_path)
        metadata = extra_info or {}
        return [Document(text=text, metadata=metadata)]
