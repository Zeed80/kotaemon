"""UI вкладки «Document Types» в Resources: CRUD, schema_def, генерация промпта, переиндексация."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

import gradio as gr

from ktem.app import BasePage
from ktem.orchestration.doc_types.generator import generate_prompt_with_llm
from ktem.orchestration.doc_types.registry import (
    DOC_TYPES,
    delete_custom_type,
    get_all_doc_types,
    get_custom_type_by_id,
    get_sources_by_doc_type,
    register_custom_type,
)


def _slugify(name: str) -> str:
    """Преобразовать display_name в slug (name)."""
    s = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "_", s).strip("_") or "custom"


class DocumentTypesManagement(BasePage):
    """Управление типами документов: базовые (readonly) + пользовательские (CRUD)."""

    def __init__(self, app):
        self._app = app
        self.selected_type_id = None
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Column():
            gr.Markdown("### Типы документов")
            gr.Markdown(
                "Базовые типы доступны по умолчанию. Пользовательские — редактирование, "
                "удаление, schema_def, переиндексация."
            )
            self.type_list = gr.DataFrame(
                headers=["id", "name", "display_name", "is_builtin"],
                interactive=False,
                label="Список типов",
                type="pandas",
            )
            self.selected_type_state = gr.State(value=None)

            with gr.Accordion("Добавить пользовательский тип", open=False):
                self.add_display_name = gr.Textbox(
                    label="Отображаемое имя",
                    placeholder="Например: Акт выполненных работ",
                )
                self.add_name = gr.Textbox(
                    label="Код (slug)",
                    placeholder="akt_vypolnennyh_rabot",
                    info="Уникальный идентификатор. Заполнится автоматически.",
                )
                self.add_keywords = gr.Textbox(
                    label="Ключевые слова (через запятую)",
                    placeholder="акт, выполненных работ, акт-приёмки",
                )
                self.add_schema_json = gr.Textbox(
                    label="Поля схемы (JSON)",
                    placeholder='[{"name": "number", "type": "str", "description": "Номер акта"}, ...]',
                    lines=5,
                    info="Список полей для экстракции. name, type (str/int/float/bool/list/dict), description.",
                )
                self.add_prompt_template = gr.Textbox(
                    label="Шаблон промпта (опционально)",
                    placeholder="Или оставьте пустым — сгенерируется автоматически.",
                    lines=3,
                )
                with gr.Row():
                    self.add_btn = gr.Button("Добавить", variant="primary")
                    self.add_generate_prompt_btn = gr.Button(
                        "Сгенерировать промпт (LLM)", variant="secondary"
                    )

            with gr.Accordion(
                "Редактировать / Удалить", open=False
            ) as self.edit_accordion:
                self.edit_type_id = gr.State(value=None)
                self.edit_display_name = gr.Textbox(label="Отображаемое имя")
                self.edit_name = gr.Textbox(label="Код (slug)", interactive=False)
                self.edit_keywords = gr.Textbox(label="Ключевые слова (через запятую)")
                self.edit_schema_json = gr.Textbox(label="Поля схемы (JSON)", lines=5)
                self.edit_prompt_template = gr.Textbox(label="Шаблон промпта", lines=5)
                with gr.Row():
                    self.edit_generate_btn = gr.Button("Сгенерировать промпт (LLM)")
                    self.edit_save_btn = gr.Button("Сохранить", variant="primary")
                    self.edit_delete_btn = gr.Button("Удалить", variant="stop")

            with gr.Accordion("Переиндексировать по типу", open=False):
                self.reindex_type_select = gr.Dropdown(
                    label="Тип документа",
                    choices=[],
                    value=None,
                )
                self.reindex_index_select = gr.Dropdown(
                    label="Индекс (коллекция)",
                    choices=[],
                    value=None,
                )
                self.reindex_btn = gr.Button("Переиндексировать", variant="primary")
                self.reindex_status = gr.Textbox(
                    label="Результат",
                    interactive=False,
                    lines=3,
                )

    def on_register_events(self):
        user_id = getattr(self._app, "user_id", None)

        def get_user_id():
            if user_id is None:
                return ""
            if hasattr(user_id, "value"):
                return user_id.value or ""
            return ""

        def load_types():
            uid = get_user_id()
            rows = get_all_doc_types(uid)
            return [
                [
                    r.get("id") or "",
                    r.get("name", ""),
                    r.get("display_name", ""),
                    r.get("is_builtin", False),
                ]
                for r in rows
            ]

        def load_custom_type_choices():
            rows = get_all_doc_types(get_user_id())
            return [
                (r["display_name"], r["name"])
                for r in rows
                if not r.get("is_builtin", True)
            ]

        def on_display_name_change(display_name):
            if display_name:
                return _slugify(display_name)
            return ""

        def add_type(display_name, name, keywords, schema_json, prompt_template):
            if not display_name or not display_name.strip():
                gr.Warning("Введите отображаемое имя.", duration=2)
                return load_types()
            slug = name.strip() if name and name.strip() else _slugify(display_name)
            if not re.match(r"^[a-z0-9_]+$", slug):
                gr.Warning(
                    "Код может содержать только буквы, цифры и подчёркивание.",
                    duration=2,
                )
                return load_types()
            if slug in DOC_TYPES:
                gr.Warning(
                    f"Тип «{slug}» уже существует как базовый.",
                    duration=2,
                )
                return load_types()
            schema_def = []
            if schema_json and schema_json.strip():
                try:
                    schema_def = json.loads(schema_json)
                    if not isinstance(schema_def, list):
                        schema_def = []
                except json.JSONDecodeError:
                    gr.Warning("Неверный JSON в полях схемы.", duration=2)
                    return load_types()
            kw_list = [k.strip() for k in (keywords or "").split(",") if k.strip()]
            classifier_keywords = {"ru": kw_list, "en": []} if kw_list else {}
            try:
                register_custom_type(
                    name=slug,
                    display_name=display_name.strip(),
                    schema_def=schema_def,
                    extraction_prompt_template=(prompt_template or "").strip(),
                    classifier_keywords=classifier_keywords,
                    user_id=get_user_id(),
                )
                gr.Info("Тип добавлен.", duration=1)
            except Exception as e:
                gr.Warning(f"Ошибка: {e}", duration=3)
            return load_types()

        def add_generate_prompt(schema_json):
            schema_def = []
            if schema_json and schema_json.strip():
                try:
                    schema_def = json.loads(schema_json)
                    if not isinstance(schema_def, list):
                        schema_def = []
                except json.JSONDecodeError:
                    gr.Warning("Введите валидный JSON схемы сначала.", duration=2)
                    return ""
            return generate_prompt_with_llm(schema_def)

        def on_row_select(evt, data):
            if evt is None or data is None:
                return (
                    gr.update(visible=False),
                    None,
                    "",
                    "",
                    "",
                    "",
                    "",
                )
            try:
                idx = getattr(evt, "index", None)
                if idx is None:
                    return (
                        gr.update(visible=False),
                        None,
                        "",
                        "",
                        "",
                        "",
                        "",
                    )
                row_idx = idx[0] if isinstance(idx, (list, tuple)) else idx
                import pandas as pd

                df = pd.DataFrame(data) if not hasattr(data, "iloc") else data
                row = df.iloc[row_idx]
                tid = row.get("id", "")
                name = row.get("name", "")
                is_builtin = row.get("is_builtin", True)
                if is_builtin or not tid:
                    return (
                        gr.update(visible=False),
                        None,
                        "",
                        "",
                        "",
                        "",
                        "",
                    )
                rec = get_custom_type_by_id(str(tid))
                if not rec:
                    return (
                        gr.update(visible=False),
                        None,
                        "",
                        "",
                        "",
                        "",
                        "",
                    )
                kw = rec.get("classifier_keywords") or {}
                kw_ru = kw.get("ru", []) if isinstance(kw, dict) else []
                keywords = ", ".join(kw_ru) if isinstance(kw_ru, list) else ""
                schema_def = rec.get("schema_def") or []
                schema_str = json.dumps(schema_def, ensure_ascii=False, indent=2)
                prompt = rec.get("extraction_prompt_template") or ""
                return (
                    gr.update(visible=True),
                    tid,
                    rec.get("display_name", ""),
                    name,
                    keywords,
                    schema_str,
                    prompt,
                )
            except Exception:
                return (
                    gr.update(visible=False),
                    None,
                    "",
                    "",
                    "",
                    "",
                    "",
                )

        def save_edit(tid, display_name, keywords, schema_json, prompt_template):
            if not tid:
                gr.Warning("Выберите тип для редактирования.", duration=1)
                return load_types()
            rec = get_custom_type_by_id(str(tid))
            if not rec:
                gr.Warning("Тип не найден.", duration=1)
                return load_types()
            name = rec["name"]
            schema_def = []
            if schema_json and schema_json.strip():
                try:
                    schema_def = json.loads(schema_json)
                    if not isinstance(schema_def, list):
                        schema_def = []
                except json.JSONDecodeError:
                    gr.Warning("Неверный JSON в полях схемы.", duration=2)
                    return load_types()
            kw_list = [k.strip() for k in (keywords or "").split(",") if k.strip()]
            classifier_keywords = {"ru": kw_list, "en": []} if kw_list else {}
            try:
                register_custom_type(
                    name=name,
                    display_name=(display_name or rec["display_name"]).strip(),
                    schema_def=schema_def,
                    extraction_prompt_template=(prompt_template or "").strip(),
                    classifier_keywords=classifier_keywords,
                    user_id=get_user_id(),
                )
                gr.Info("Тип обновлён.", duration=1)
            except Exception as e:
                gr.Warning(f"Ошибка: {e}", duration=3)
            return load_types()

        def do_delete(tid):
            if not tid:
                gr.Warning("Выберите тип для удаления.", duration=1)
                return load_types(), gr.update(visible=False)
            rec = get_custom_type_by_id(str(tid))
            if not rec:
                gr.Warning("Тип не найден.", duration=1)
                return load_types(), gr.update(visible=False)
            if delete_custom_type(rec["name"], get_user_id()):
                gr.Info("Тип удалён.", duration=1)
            else:
                gr.Warning("Не удалось удалить (возможно, базовый тип).", duration=2)
            return load_types(), gr.update(visible=False)

        def edit_generate_prompt(schema_json, display_name):
            schema_def = []
            if schema_json and schema_json.strip():
                try:
                    schema_def = json.loads(schema_json)
                    if not isinstance(schema_def, list):
                        schema_def = []
                except json.JSONDecodeError:
                    gr.Warning("Введите валидный JSON схемы.", duration=2)
                    return ""
            return generate_prompt_with_llm(schema_def, display_name or "")

        def load_reindex_choices():
            custom = load_custom_type_choices()
            indices = [
                (f"{idx.name} (id={idx.id})", idx.id)
                for idx in self._app.index_manager.indices
            ]
            return (
                gr.update(choices=custom, value=custom[0][1] if custom else None),
                gr.update(choices=indices, value=indices[0][1] if indices else None),
            )

        def do_reindex(doc_type, index_id):
            if not doc_type or not index_id:
                return "Укажите тип и индекс."
            index_obj = None
            for idx in self._app.index_manager.indices:
                if idx.id == index_id:
                    index_obj = idx
                    break
            if not index_obj:
                return "Индекс не найден."
            Source = index_obj._resources["Source"]
            sources = get_sources_by_doc_type(Source, doc_type, get_user_id())
            if not sources:
                return f"Документов с типом «{doc_type}» в выбранном индексе нет."
            fs_path = index_obj._fs_path
            settings = self._app.default_settings.flatten()
            settings[f"index.options.{index_id}.doc_type_override"] = doc_type
            pipeline = index_obj.get_indexing_pipeline(
                settings, get_user_id() or "default"
            )
            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from ktem.db.engine import engine

            reindexed = 0
            errors = []
            for source_id, path_hash in sources:
                try:
                    stored = Path(fs_path) / path_hash
                    if not stored.exists():
                        continue
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with Session(engine) as session:
                            src = (
                                session.execute(
                                    select(Source).where(Source.id == source_id)
                                )
                                .scalars()
                                .first()
                            )
                        if not src:
                            continue
                        orig_name = getattr(src, "name", path_hash)
                        tmp_file = Path(tmpdir) / orig_name
                        shutil.copy(stored, tmp_file)
                        pipeline.delete_file(source_id)
                        _iter = pipeline.stream([str(tmp_file)], reindex=True)
                        list(_iter)
                        reindexed += 1
                except Exception as e:
                    errors.append(str(e))
            msg = f"Переиндексировано: {reindexed} из {len(sources)}."
            if errors:
                msg += f"\nОшибки: {'; '.join(errors[:3])}"
            return msg

        self._app.app.load(
            fn=load_types,
            outputs=[self.type_list],
        )

        self._app.app.load(
            fn=load_reindex_choices,
            outputs=[self.reindex_type_select, self.reindex_index_select],
        )

        self.add_display_name.change(
            fn=on_display_name_change,
            inputs=[self.add_display_name],
            outputs=[self.add_name],
        )

        self.add_btn.click(
            fn=add_type,
            inputs=[
                self.add_display_name,
                self.add_name,
                self.add_keywords,
                self.add_schema_json,
                self.add_prompt_template,
            ],
            outputs=[self.type_list],
        ).then(
            fn=lambda: (
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
            ),
            outputs=[
                self.add_display_name,
                self.add_name,
                self.add_keywords,
                self.add_schema_json,
                self.add_prompt_template,
            ],
        )

        self.add_generate_prompt_btn.click(
            fn=add_generate_prompt,
            inputs=[self.add_schema_json],
            outputs=[self.add_prompt_template],
        )

        self.type_list.select(
            fn=on_row_select,
            inputs=[self.type_list],
            outputs=[
                self.edit_accordion,
                self.edit_type_id,
                self.edit_display_name,
                self.edit_name,
                self.edit_keywords,
                self.edit_schema_json,
                self.edit_prompt_template,
            ],
        )

        self.edit_save_btn.click(
            fn=save_edit,
            inputs=[
                self.edit_type_id,
                self.edit_display_name,
                self.edit_keywords,
                self.edit_schema_json,
                self.edit_prompt_template,
            ],
            outputs=[self.type_list],
        )

        self.edit_delete_btn.click(
            fn=do_delete,
            inputs=[self.edit_type_id],
            outputs=[self.type_list, self.edit_accordion],
        )

        self.edit_generate_btn.click(
            fn=edit_generate_prompt,
            inputs=[self.edit_schema_json, self.edit_display_name],
            outputs=[self.edit_prompt_template],
        )

        self.reindex_btn.click(
            fn=do_reindex,
            inputs=[self.reindex_type_select, self.reindex_index_select],
            outputs=[self.reindex_status],
        ).then(
            fn=load_reindex_choices,
            outputs=[self.reindex_type_select, self.reindex_index_select],
        )
