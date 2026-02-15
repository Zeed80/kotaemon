# Где хранятся данные Kotaemon и полный сброс

## Расположение данных

### 1. Docker (volumes — переживают удаление проекта)

| Volume                   | Путь в контейнере    | Содержимое                |
| ------------------------ | -------------------- | ------------------------- |
| `kotaemon_ktem_app_data` | `/app/ktem_app_data` | Всё приложение            |
| `kotaemon_qdrant_data`   | `/qdrant/storage`    | Векторный индекс (Qdrant) |

**ktem_app_data** содержит:

- `user_data/sql.db` — SQLite: пользователи, индексы, настройки LLM/Embeddings/Rerankings
- `user_data/files/` — загруженные файлы
- `user_data/docstore/` — LanceDB docstore
- `application_settings.json` — General (Ollama URL, GraphRAG, и т.д.)
- `markdown_cache_dir/`, `chunks_cache_dir/`, `zip_cache_dir*/`
- `huggingface/` — кэш моделей HF

### 2. Локальный запуск (без Docker)

- `./ktem_app_data/` — в корне проекта (рядом с flowsettings.py)
- Qdrant: `localhost:6333` или `QDRANT_PATH` для file-режима

### 3. Прочее (вне проекта)

- `~/.cache/huggingface/` — если HF_HOME не переопределён
- `~/.cache/pip/`, `~/.cache/uv/` — кэш пакетов

---

## Почему после «удаления» остались настройки

При **Docker** volumes не привязаны к папке проекта. Команда `docker compose down` не удаляет volumes. Данные в `kotaemon_ktem_app_data` сохраняются.

Чтобы полностью сбросить данные в Docker:

```bash
docker compose down -v
docker volume rm kotaemon_ktem_app_data kotaemon_qdrant_data 2>/dev/null || true
docker compose up -d
```

---

## Пропавшие пункты в Settings (Web UI)

### Влияние `KH_FEATURE_USER_MANAGEMENT=false` (в docker-compose)

При отключённом управлении пользователями:

- **Скрывается вкладка «User settings»** (смена пароля, Logout)
- Остальные вкладки (General, Retrieval settings, Reasoning, Ollama servers) должны быть

### Влияние `.env` и `application_settings.json`

- **General**: Ollama URL, reranker, Qdrant (URL, API key, path, hybrid, sparse model), флаги GraphRAG — из `SETTINGS_APP` и `application_settings.json`
- **Retrieval settings**: LLM, Embedding, VLM для каждого индекса — из БД и `flowsettings`
- **Reasoning**: модель, язык и т.п. — из БД

Если в `.env` нет ключей (OPENAI_API_KEY, GOOGLE_API_KEY и т.д.), соответствующие провайдеры в flowsettings не создаются → меньше вариантов в селекторах.

---

## Проверка Web UI

Убедитесь, что:

1. В Settings есть вкладки: **Ollama servers**, **General**, **Retrieval settings**, **Reasoning settings**
2. В `.env` заданы нужные API-ключи (OpenAI, Google, и т.д.) для нужных провайдеров
3. Для шифрования ключей в БД задайте `KH_ENCRYPTION_KEY` в `.env` (рекомендуется для production)
4. После полного сброса volumes (см. выше) UI загружается с дефолтами

---

## Полный сброс (Docker)

```bash
# Остановить и удалить volumes
docker compose down -v

# Удалить volumes вручную (если -v не сработало)
docker volume ls | grep kotaemon
docker volume rm kotaemon_ktem_app_data kotaemon_qdrant_data

# Запустить заново
docker compose up -d
```

После этого данные обнуляются, приложение стартует как при первом запуске.
