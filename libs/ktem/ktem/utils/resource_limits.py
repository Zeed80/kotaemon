"""Автоопределение лимитов ресурсов: GPU VRAM, модели, batch sizes.

Используется для рекомендаций настроек и предупреждений о нехватке памяти.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Результат определения лимитов ресурсов."""

    gpu_vram_mb: int = 0
    gpu_name: str = ""
    cpu_only: bool = True
    # Примерные требования моделей (MB)
    model_vram_estimates: dict[str, int] = field(default_factory=lambda: {
        "7b": 8 * 1024,   # ~8 GB для 7B в fp16
        "8b": 9 * 1024,
        "13b": 14 * 1024,
        "32b": 20 * 1024,  # quantized
        "70b": 40 * 1024,  # quantized
        "embedding": 2 * 1024,
        "reranker": 2 * 1024,
    })
    suggested_max_context: int = 64000
    suggested_batch_size: int = 32
    warnings: list[str] = field(default_factory=list)


def _get_nvidia_smi_vram() -> tuple[int, str]:
    """Получить объём VRAM и имя GPU через nvidia-smi."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return 0, ""
        line = out.stdout.strip().split("\n")[0]
        parts = line.split(",")
        if len(parts) >= 2:
            vram_str = parts[0].strip()
            name = parts[1].strip()
            vram_mb = int(re.sub(r"[^\d]", "", vram_str) or "0")
            return vram_mb, name
        return 0, ""
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError) as e:
        logger.debug("nvidia-smi not available: %s", e)
        return 0, ""


def _estimate_model_vram(model_name: str) -> int:
    """Оценка VRAM для модели по имени (MB)."""
    model_lower = model_name.lower()
    for pattern, mb in [
        (r"70b|70b-", 40 * 1024),
        (r"32b|32b-", 20 * 1024),
        (r"13b|13b-", 14 * 1024),
        (r"8b|8b-", 9 * 1024),
        (r"7b|7b-", 8 * 1024),
        (r"3b|3b-", 4 * 1024),
        (r"1b|1b-", 2 * 1024),
        (r"embed|bge|nomic|e5", 2 * 1024),
        (r"rerank", 2 * 1024),
    ]:
        if re.search(pattern, model_lower):
            return mb
    return 4 * 1024  # default


def detect_resource_limits() -> ResourceLimits:
    """
    Определить лимиты ресурсов системы.

    Returns:
        ResourceLimits с VRAM, рекомендованными настройками и предупреждениями.
    """
    limits = ResourceLimits()
    vram_mb, gpu_name = _get_nvidia_smi_vram()

    if vram_mb > 0:
        limits.gpu_vram_mb = vram_mb
        limits.gpu_name = gpu_name
        limits.cpu_only = False

        if vram_mb < 4 * 1024:
            limits.warnings.append(
                f"GPU VRAM {vram_mb // 1024} GB — для LLM рекомендуется 8+ GB"
            )
            limits.suggested_max_context = 16000
            limits.suggested_batch_size = 8
        elif vram_mb < 8 * 1024:
            limits.suggested_max_context = 32000
            limits.suggested_batch_size = 16
        elif vram_mb < 16 * 1024:
            limits.suggested_max_context = 64000
            limits.suggested_batch_size = 32
        elif vram_mb < 24 * 1024:
            limits.suggested_max_context = 64000
            limits.suggested_batch_size = 64
        else:
            limits.suggested_max_context = 128000
            limits.suggested_batch_size = 128
    else:
        limits.warnings.append("GPU не обнаружен — используются лимиты для CPU")
        limits.suggested_max_context = 32000
        limits.suggested_batch_size = 8

    return limits


def get_limits_summary() -> dict[str, Any]:
    """Краткая сводка для UI (Settings)."""
    limits = detect_resource_limits()
    return {
        "gpu_vram_mb": limits.gpu_vram_mb,
        "gpu_name": limits.gpu_name,
        "cpu_only": limits.cpu_only,
        "suggested_max_context": limits.suggested_max_context,
        "suggested_batch_size": limits.suggested_batch_size,
        "warnings": limits.warnings,
    }


def format_limits_html() -> str:
    """HTML-блок с информацией о ресурсах для Settings."""
    limits = detect_resource_limits()
    if limits.cpu_only:
        gpu_line = "<span style='color: gray'>GPU не обнаружен (CPU режим)</span>"
    else:
        gpu_line = (
            f"<strong>{limits.gpu_name}</strong> — "
            f"{limits.gpu_vram_mb // 1024} GB VRAM"
        )
    warnings_html = ""
    if limits.warnings:
        warnings_html = (
            "<ul style='margin: 4px 0; color: #b45309'>"
            + "".join(f"<li>{w}</li>" for w in limits.warnings)
            + "</ul>"
        )
    return (
        "<div style='font-size: 0.9em; margin-top: 8px'>"
        f"<div>{gpu_line}</div>"
        f"<div>Рекомендуемый max context: {limits.suggested_max_context // 1000}k токенов</div>"
        f"{warnings_html}"
        "</div>"
    )
