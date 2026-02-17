"""Pydantic-схемы для структурированной экстракции документов."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# --- Invoice ---


class Requisites(BaseModel):
    """Реквизиты организации."""

    inn: str | None = Field(None, description="ИНН")
    kpp: str | None = Field(None, description="КПП")
    company_name: str | None = Field(None, description="Наименование организации")
    address: str | None = Field(None, description="Адрес")
    bank_details: str | None = Field(None, description="Банковские реквизиты")


class LineItem(BaseModel):
    """Позиция в счёте."""

    name: str = Field(..., description="Наименование товара/услуги")
    quantity: float | None = Field(None, description="Количество")
    unit: str | None = Field(None, description="Единица измерения")
    price: float | None = Field(None, description="Цена за единицу")
    amount: float | None = Field(None, description="Сумма")


class InvoiceSchema(BaseModel):
    """Структурированные данные счёта."""

    requisites_seller: Requisites | None = Field(None, description="Реквизиты продавца")
    requisites_buyer: Requisites | None = Field(
        None, description="Реквизиты покупателя"
    )
    invoice_number: str | None = Field(None, description="Номер счёта")
    date: str | None = Field(None, description="Дата")
    line_items: list[LineItem] = Field(default_factory=list, description="Позиции")
    total: float | None = Field(None, description="Итого к оплате")
    currency: str | None = Field(None, description="Валюта")


# --- Letter ---


class LetterSchema(BaseModel):
    """Структурированные данные письма."""

    sender: str | None = Field(None, description="Отправитель")
    recipient: str | None = Field(None, description="Получатель")
    date: str | None = Field(None, description="Дата")
    subject: str | None = Field(None, description="Тема")
    body_summary: str | None = Field(None, description="Краткое содержание")


# --- Tech Spec ---


class Section(BaseModel):
    """Секция техкарты."""

    name: str = Field(..., description="Название секции")
    content: str = Field(..., description="Содержимое")


class TechSpecSchema(BaseModel):
    """Структурированные данные техкарты/технической спецификации."""

    title: str | None = Field(None, description="Заголовок документа")
    sections: list[Section] = Field(default_factory=list, description="Секции")
    tables: list[str] = Field(default_factory=list, description="Таблицы в markdown")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Параметры")


# --- Drawing ---


class DrawingElement(BaseModel):
    """Элемент чертежа."""

    element_type: str = Field(..., description="Тип: hole, groove, surface, etc.")
    description: str = Field(..., description="Описание элемента")
    dimensions: str | None = Field(None, description="Геометрические размеры")
    tolerance: str | None = Field(None, description="Допуски")
    coordinates: str | None = Field(None, description="Координаты расположения")
    view: str | None = Field(None, description="Вид/проекция")


class TitleBlock(BaseModel):
    """Штамп чертежа."""

    name: str | None = Field(None, description="Наименование")
    scale: str | None = Field(None, description="Масштаб")
    document_number: str | None = Field(None, description="Обозначение")
    material: str | None = Field(None, description="Материал")


class DrawingSchema(BaseModel):
    """Структурированные данные чертежа."""

    title_block: TitleBlock | None = Field(None, description="Штамп")
    elements: list[DrawingElement] = Field(default_factory=list, description="Элементы")


# --- Sketch ---


class SketchSchema(BaseModel):
    """Структурированные данные эскиза."""

    description: str = Field(..., description="Общее описание")
    main_elements: list[str] = Field(
        default_factory=list, description="Основные элементы"
    )
    dimensions: str | None = Field(None, description="Габаритные размеры")


# Реестр схем по типу документа
SCHEMAS: dict[str, type[BaseModel]] = {
    "invoice": InvoiceSchema,
    "letter": LetterSchema,
    "tech_spec": TechSpecSchema,
    "drawing": DrawingSchema,
    "sketch": SketchSchema,
}

# Типы с поддержкой структурированной экстракции
DOC_TYPES_WITH_SCHEMAS = tuple(SCHEMAS.keys())
