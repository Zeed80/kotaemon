# feat(doc-types): Document Types, document_links + LightRAG, docs, CI

## Summary

- **Document Types**: CRUD для типов документов, schema_def, генерация промптов через LLM, переиндексация по типу.
- **document_links + LightRAG**: Связи между документами (напр. счёт → контракт) сохраняются в `Source.note` и автоматически добавляются в граф LightRAG как рёбра.
- **Документация**: `docs/pages/app/index/document-types.md`, README Key Features, обновлён `file.md`.
- **CI**: `migration-check` workflow для проверки Alembic-миграций на PostgreSQL.
- **Fixes**: ruff E741, mypy (embeddings/ui, api/routes), codespell i18n.

## Checklist

- [x] Pre-commit пройден
- [x] Тесты `ktem_tests/test_doc_types` проходят
- [x] Документация обновлена

## Merge

После code review:

```bash
git push -u origin feat/document-types-and-links
```

Создать PR на GitHub и смержить в `main`.
