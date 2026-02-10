# Отчёт о совместимости элементов проекта Kotaemon

**Дата:** 2026-02-10  
**Репозиторий:** `J:/Project/kotaemon`

## 1. Резюме

Проведена проверка совместимости всех элементов проекта: зависимости, конфигурация, flowsettings, типы индексов, LLM/embeddings/rerankings, Docker, CI и локальная установка.

---

## 2. Версия Python

| Файл | Значение | Статус |
|------|----------|--------|
| `.python-version` | `3.1` | **Ошибка** — устаревшая/некорректная версия. Проект требует Python >= 3.10. Исправить на `3.10` или `3.11`. |
| `pyproject.toml` (корень) | `requires-python = ">= 3.10"` | OK |
| `libs/kotaemon/pyproject.toml` | `requires-python = ">= 3.10"` | OK |
| `libs/ktem/pyproject.toml` | `requires-python = ">= 3.10"` | OK |
| `Dockerfile` | `python:3.10-slim` | OK |
| `unit-test.yaml` | matrix: "3.10", "3.11" | OK |

---

## 3. Зависимости (kotaemon)

### Основные пакеты
- `langchain>=0.1.16,<0.2.16` — совместимо (текущая 0.2.15)
- `gradio>=4.31.0,<5` — совместимо с ktem
- `chromadb>=0.5.0,<=0.5.16` — зафиксировано для совместимости с langchain/llama-index
- `pydantic>=2.0.0,<=2.10.6` — диапазон ограничен
- `fastapi>=0.112.0,<=0.112.1` — узкий диапазон
- `theflow>=0.8.6,<0.9.0` — OK

### Опциональные (adv)
- `graphrag<=0.3.6` — в Dockerfile для full образа
- `lightrag-hku<=1.3.0` — в Dockerfile
- `nano-graphrag` — в Dockerfile (full); при lite выдаётся предупреждение

### Потенциальные конфликты
- **hnswlib vs chroma-hnswlib**: Dockerfile full образа выполняет `pip uninstall hnswlib chroma-hnswlib; pip install chroma-hnswlib` после установки nano-graphrag — обход конфликта учтён.

---

## 4. flowsettings.py ↔ компоненты

### LLM (kotaemon.llms)
| flowsettings | Класс | Экспорт в __init__ |
|--------------|-------|---------------------|
| ChatOpenAI | ✅ | ✅ |
| AzureChatOpenAI | ✅ | ✅ |
| LCOllamaChat | ✅ | ✅ |
| LCAnthropicChat | ✅ | ✅ |
| LCGeminiChat | ✅ | ✅ |
| LCCohereChat | ✅ | ✅ |

### Embeddings (kotaemon.embeddings)
| flowsettings | Класс | Экспорт |
|--------------|-------|---------|
| OpenAIEmbeddings | ✅ | ✅ |
| AzureOpenAIEmbeddings | ✅ | ✅ |
| VoyageAIEmbeddings | ✅ | ✅ |
| LCCohereEmbeddings | ✅ | ✅ |
| LCGoogleEmbeddings | ✅ | ✅ |
| LCMistralEmbeddings | ✅ | ✅ |
| FastEmbedEmbeddings | ✅ | ✅ |

### Rerankings (kotaemon.rerankings)
| flowsettings | Класс | Экспорт |
|--------------|-------|---------|
| VoyageAIReranking | ✅ | ✅ |
| CohereReranking | ✅ | ✅ |
| OllamaReranking | ✅ | ✅ |

### Storages (kotaemon.storages)
| flowsettings | Класс | Экспорт |
|--------------|-------|---------|
| LanceDBDocumentStore | ✅ | ✅ |
| ChromaVectorStore | ✅ | ✅ |

### Retrievers (kotaemon.indices.retrievers)
| flowsettings KH_WEB_SEARCH_BACKEND | Модуль | Статус |
|------------------------------------|--------|--------|
| `kotaemon.indices.retrievers.tavily_web_search.WebSearch` | ✅ | OK |
| `kotaemon.indices.retrievers.jina_web_search.WebSearch` | ✅ | OK (закомментирован) |

### Индексы (ktem.index.file)
| flowsettings KH_INDEX_TYPES | Класс | Существует |
|-----------------------------|-------|------------|
| ktem.index.file.FileIndex | ✅ | ✅ |
| ktem.index.file.graph.GraphRAGIndex | ✅ | ✅ (MS GraphRAG) |
| ktem.index.file.graph.NanoGraphRAGIndex | ✅ | ✅ |
| ktem.index.file.graph.LightRAGIndex | ✅ | ✅ |

### Reasoning (ktem.reasoning)
| flowsettings KH_REASONINGS | Класс | Существует |
|---------------------------|-------|------------|
| ktem.reasoning.simple.FullQAPipeline | ✅ | ✅ |
| ktem.reasoning.simple.FullDecomposeQAPipeline | ✅ | ✅ |
| ktem.reasoning.react.ReactAgentPipeline | ✅ | ✅ |
| ktem.reasoning.rewoo.RewooAgentPipeline | ✅ | ✅ |

---

## 5. Опциональные настройки flowsettings

| Переменная | Использование | flowsettings |
|------------|---------------|--------------|
| `KH_EMBEDDING_LLM` | ktem/embeddings/db.py | Не задана — используется `hasattr`, fallback на BaseEmbeddingTable |
| `KH_TABLE_LLM` | ktem/llms/db.py | Не задана — fallback |
| `KH_TABLE_RERANKING` | ktem/rerankings/db.py | Не задана — fallback |
| `USE_GLOBAL_GRAPHRAG` | nano_pipelines.py, lightrag_pipelines.py | ✅ Задана |

---

## 6. Установка и точки входа

| Метод | Команда/файл | Зависимости |
|-------|--------------|-------------|
| Корневой pyproject.toml | `kotaemon` и `ktem` из git | Используется для публикации пакета |
| install.sh --local | `pip install -e "libs/kotaemon[all]" -e "libs/ktem"` | Локальные libs |
| Dockerfile lite | `pip install -e "libs/kotaemon"` (без [all]) | Минимальный набор |
| Dockerfile full | `pip install -e "libs/kotaemon[adv]"` + graphrag, lightrag, nano-graphrag, docling | Полный набор |
| unit-test.yaml | `pip install -e "libs/kotaemon[all]"` + `pip install -e "libs/ktem"` | Совпадает с install.sh |

---

## 7. mkdocs.yml

- `paths: [libs/kotaemon/kotaemon]` — путь к документации API совпадает со структурой пакета.
- `docs/scripts/generate_reference_docs.py` — путь к скрипту генерации корректен.

---

## 8. Pre-commit и CI

| Компонент | Версия | Совместимость |
|-----------|--------|---------------|
| pre-commit-hooks | v5.0.0 | OK |
| black | 24.10.0 | OK |
| isort | 5.13.2 | OK |
| flake8 | 7.0.0 | OK |
| ruff-pre-commit | v0.8.0 | OK (если ruff-check доступен) |
| mypy | v1.13.0 | OK |

Примечание: в `reports/quality_inspection_2026-02-10.md` указано, что `ruff-check` может отсутствовать в репозитории ruff-pre-commit — стоит проверить актуальный id хука.

---

## 9. Рекомендации

### Критично
1. **Исправить `.python-version`**: заменить `3.1` на `3.10` или `3.11`.

### Желательно
2. Добавить в документацию явное указание, что `KH_EMBEDDING_LLM`, `KH_TABLE_LLM`, `KH_TABLE_RERANKING` опциональны и используются только при `KH_ENABLE_ALEMBIC=True`.
3. В lite-режиме (без GraphRAG/LightRAG/Nano) при включённых `USE_*_GRAPHRAG` показывать пользователю понятное предупреждение о необходимости full-образа или установки соответствующих пакетов.

### Опционально
4. Обновить `doc_env_reqs.txt` и проверить совместимость с `mkdocs-material` 9.x.
5. Добавить `requirements.txt` в корень для тех, кто не использует `pip install -e`.

---

## 10. Проверка импорта (фактическая)

```
flowsettings OK
ktem.index.file.FileIndex OK
ktem.index.file.graph.GraphRAGIndex OK (с предупреждениями о graphrag/lightrag/nano-graphrag при lite)
```

Все классы из flowsettings успешно импортируются при корректном PYTHONPATH и `THEFLOW_SETTINGS_MODULE=flowsettings`.
