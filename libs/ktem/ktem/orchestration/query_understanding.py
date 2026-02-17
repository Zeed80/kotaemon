"""Определение намерения запроса для SQL-first retrieval."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "query_understanding.txt"


@dataclass
class QueryIntent:
    """Результат анализа запроса."""

    intent: str  # sql_only | vector_only | hybrid
    sql_filters: dict[str, Any]


def _load_prompt() -> str:
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8")
    return (
        "Analyze the user query. Respond with valid JSON: "
        '{"intent": "sql_only"|"vector_only"|"hybrid", "sql_filters": {...}}. '
        "Output ONLY valid JSON."
    )


def understand_query(
    query: str,
    llm=None,
    *,
    skip_llm: bool = False,
) -> QueryIntent:
    """
    Определить намерение запроса и SQL-фильтры.

    Args:
        query: запрос пользователя
        llm: LLM для анализа (опционально)
        skip_llm: если True, возвращает vector_only без вызова LLM

    Returns:
        QueryIntent с intent и sql_filters
    """
    if skip_llm or not query or not query.strip():
        return QueryIntent(intent="vector_only", sql_filters={})

    if not llm:
        try:
            from ktem.llms.manager import llms

            llm = llms.get_default()
        except Exception:
            return QueryIntent(intent="vector_only", sql_filters={})

    if not llm:
        return QueryIntent(intent="vector_only", sql_filters={})

    prompt = _load_prompt() + "\n\nUser query: " + query[:2000]
    try:
        from langchain_core.messages import HumanMessage

        if callable(llm):
            resp = llm([HumanMessage(content=prompt)])
        else:
            resp = llm(prompt)
        text = getattr(resp, "text", None) or getattr(resp, "content", str(resp))
    except Exception as e:
        logger.warning("Query understanding failed: %s", e)
        return QueryIntent(intent="vector_only", sql_filters={})

    text = (text or "").strip()
    for start in ("{", "```json"):
        idx = text.find(start)
        if idx >= 0:
            if start == "```json":
                idx += len("```json")
            json_str = text[idx:].split("```")[0].strip()
            try:
                data = json.loads(json_str)
                intent = str(data.get("intent", "vector_only"))
                if intent not in ("sql_only", "vector_only", "hybrid"):
                    intent = "vector_only"
                filters = data.get("sql_filters") or {}
                if not isinstance(filters, dict):
                    filters = {}
                return QueryIntent(intent=intent, sql_filters=filters)
            except json.JSONDecodeError:
                continue
    return QueryIntent(intent="vector_only", sql_filters={})
