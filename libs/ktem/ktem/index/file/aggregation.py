"""Pre-aggregation: извлечение агрегатов из таблиц при индексации.

Создаёт сводные документы (топ позиций, суммы, даты) для запросов вида
«наиболее покупаемое», «итого по документам» и т.п. Работает в фоне при индексации.
"""

from __future__ import annotations

import csv
import logging
import re
from io import StringIO

from kotaemon.base import Document

logger = logging.getLogger(__name__)

# Ключевые слова для определения столбцов (ru, en, и др.)
COL_ITEM_KEYWORDS = (
    "наименование",
    "название",
    "товар",
    "продукт",
    "item",
    "name",
    "product",
    "description",
    "описание",
    "article",
    "артикул",
)
COL_QUANTITY_KEYWORDS = (
    "количество",
    "кол-во",
    "qty",
    "quantity",
    "шт",
)
COL_PRICE_KEYWORDS = (
    "цена",
    "price",
    "стоимость",
)
COL_AMOUNT_KEYWORDS = (
    "сумма",
    "amount",
    "итого",
    "total",
    "sum",
    "всего",
)


def _parse_table_to_rows(table_content: str) -> list[list[str]]:
    """Парсит таблицу из markdown или CSV в список строк."""
    if not table_content or not table_content.strip():
        return []

    lines = [
        line.strip() for line in table_content.strip().splitlines() if line.strip()
    ]
    if not lines:
        return []

    # Markdown table
    if lines[0].startswith("|"):
        rows = []
        for line in lines:
            if line.startswith("|") and "---" not in line:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells:
                    rows.append(cells)
        return rows

    # CSV
    try:
        reader = csv.reader(StringIO(table_content))
        return [row for row in reader if any(cell.strip() for cell in row)]
    except Exception:
        pass
    return []


def _detect_column_indices(header: list[str]) -> dict[str, int]:
    """Определяет индексы столбцов по заголовкам."""
    header_lower = [h.lower().strip() for h in header]
    result: dict[str, int] = {}

    for i, h in enumerate(header_lower):
        if any(kw in h for kw in COL_ITEM_KEYWORDS):
            result.setdefault("item", i)
        if any(kw in h for kw in COL_QUANTITY_KEYWORDS):
            result.setdefault("quantity", i)
        if any(kw in h for kw in COL_PRICE_KEYWORDS):
            result.setdefault("price", i)
        if any(kw in h for kw in COL_AMOUNT_KEYWORDS):
            result.setdefault("amount", i)

    return result


def _parse_number(s: str) -> float | None:
    """Парсит число из строки (с учётом разделителей)."""
    if not s:
        return None
    s = str(s).strip().replace(",", ".").replace(" ", "")
    s = re.sub(r"[^\d.-]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def extract_aggregates_from_table(
    table_content: str,
    file_name: str = "",
    page_label: str | None = None,
) -> list[dict]:
    """
    Извлекает агрегаты из таблицы (счета, прайсы, техкарты).

    Returns:
        Список словарей с ключами: summary_text, type, metadata
    """
    rows = _parse_table_to_rows(table_content)
    if len(rows) < 2:
        return []

    header = rows[0]
    data_rows = rows[1:]
    cols = _detect_column_indices(header)

    if not cols:
        return []

    item_idx = cols.get("item", 0)
    qty_idx = cols.get("quantity")
    price_idx = cols.get("price")
    amount_idx = cols.get("amount")

    items_with_qty: list[tuple[str, float]] = []
    items_with_amount: list[tuple[str, float]] = []
    total_sum = 0.0

    for row in data_rows:
        if len(row) <= max(item_idx, qty_idx or 0, price_idx or 0, amount_idx or 0):
            continue

        item_name = str(row[item_idx]).strip() if item_idx < len(row) else ""
        if not item_name:
            continue

        qty = (
            _parse_number(row[qty_idx])
            if qty_idx is not None and qty_idx < len(row)
            else None
        )
        amt = (
            _parse_number(row[amount_idx])
            if amount_idx is not None and amount_idx < len(row)
            else None
        )
        prc = (
            _parse_number(row[price_idx])
            if price_idx is not None and price_idx < len(row)
            else None
        )

        if qty is not None and qty > 0:
            items_with_qty.append((item_name, qty))
        if amt is not None and amt > 0:
            items_with_amount.append((item_name, amt))
            total_sum += amt
        elif qty is not None and prc is not None:
            calc = qty * prc
            items_with_amount.append((item_name, calc))
            total_sum += calc

    results: list[dict] = []

    # Сводка: топ по количеству
    if items_with_qty:
        top_qty = sorted(items_with_qty, key=lambda x: x[1], reverse=True)[:20]
        lines = [
            "AGGREGATE: Топ позиций по количеству",
            "",
            "| Позиция | Количество |",
            "|---------|------------|",
        ]
        for name, q in top_qty:
            name_short = name[:80] + "…" if len(name) > 80 else name
            lines.append(f"| {name_short} | {q} |")
        results.append(
            {
                "summary_text": "\n".join(lines),
                "type": "aggregate_top_quantity",
                "metadata": {"file_name": file_name, "page_label": page_label},
            }
        )

    # Сводка: топ по сумме
    if items_with_amount:
        top_amt = sorted(items_with_amount, key=lambda x: x[1], reverse=True)[:20]
        lines = [
            "AGGREGATE: Топ позиций по сумме",
            "",
            "| Позиция | Сумма |",
            "|---------|-------|",
        ]
        for name, a in top_amt:
            name_short = name[:80] + "…" if len(name) > 80 else name
            lines.append(f"| {name_short} | {a:.2f} |")
        if total_sum > 0:
            lines.append("")
            lines.append(f"ИТОГО: {total_sum:.2f}")
        results.append(
            {
                "summary_text": "\n".join(lines),
                "type": "aggregate_top_amount",
                "metadata": {"file_name": file_name, "page_label": page_label},
            }
        )

    return results


def create_aggregate_documents(
    docs: list[Document],
    file_id: str,
    file_name: str,
) -> list[Document]:
    """
    Создаёт документы-агрегаты из таблиц в списке docs.

    Args:
        docs: документы с type="table" (имеют table_origin в metadata)
        file_id: id файла
        file_name: имя файла

    Returns:
        Список Document с type="aggregate" для индексации
    """
    aggregate_docs: list[Document] = []
    seen_texts: set[str] = set()

    for doc in docs:
        if doc.metadata.get("type") != "table":
            continue
        table_content = doc.metadata.get("table_origin") or doc.text
        if not table_content:
            continue

        page_label = doc.metadata.get("page_label")
        try:
            aggregates = extract_aggregates_from_table(
                table_content,
                file_name=file_name,
                page_label=str(page_label) if page_label is not None else None,
            )
        except Exception as e:
            logger.warning("Pre-aggregation failed for %s: %s", file_name, e)
            continue

        for agg in aggregates:
            text = agg["summary_text"]
            if text in seen_texts:
                continue
            seen_texts.add(text)

            meta = {
                "type": "aggregate",
                "file_id": file_id,
                "file_name": file_name,
                "aggregate_type": agg["type"],
            }
            if page_label is not None:
                meta["page_label"] = page_label
            meta.update(agg.get("metadata", {}))

            aggregate_docs.append(Document(text=text, metadata=meta))

    return aggregate_docs
