---
name: kotaemon-rag-pipeline
description: Паттерны RAG-пайплайнов kotaemon. Использовать при разработке reasoning/indexing/retrieval.
---

# Kotaemon RAG Pipeline

## Компоненты

- **Reasoning**: `ktem.reasoning.simple`, `ktem.reasoning.react`, `ktem.reasoning.rewoo`
- **Indexing**: `ktem.index.file.FileIndex`, `ktem.index.file.graph.*` (GraphRAG, NanoGraphRAG, LightRAG)
- **Retrieval**: VectorStore, DocumentStore, Retriever

## flowsettings (flowsettings.py)

| Константа      | Назначение                    |
|----------------|-------------------------------|
| KH_DOCSTORE    | Хранилище документов          |
| KH_VECTORSTORE | Векторное хранилище           |
| KH_REASONINGS  | Список пайплайнов reasoning   |
| KH_INDEX_TYPES | Типы индексации               |
| KH_LLMS        | LLM-провайдеры                |
| KH_EMBEDDINGS  | Модели эмбеддингов            |
| KH_RERANKINGS  | Модели переранжирования       |

## Добавление нового Reasoning

1. Создать класс в `libs/ktem/ktem/reasoning/`
2. Наследовать `BaseReasoning` или `BaseComponent`
3. Добавить в flowsettings: `KH_REASONINGS.append("ktem.reasoning.mymodule.MyPipeline")`
4. При необходимости добавить в `SETTINGS_REASONING`

## Добавление нового Index Type

1. Создать класс в `libs/ktem/ktem/index/file/`
2. Реализовать интерфейс индексации
3. Добавить в `KH_INDEX_TYPES` и `KH_INDICES`

## MCP

- **context7**: актуальная документация библиотек
- **Magic MCP**: frontend / Gradio компоненты
