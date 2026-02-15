# Где хранятся данные Kotaemon и полный сброс

## Настройки из Web UI → .env

Все настройки (API-ключи, Qdrant, Ollama и т.д.) редактируются в **Settings → General**. При сохранении значения записываются в `.env` — редактирование `.env` вручную не требуется.

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

---

## Настройка Qdrant (векторное хранилище)

Qdrant используется по умолчанию для хранения векторных индексов. Настройки в **Settings → General**.

### Docker Compose

- Сервис `qdrant` поднимается автоматически (`docker compose up`)
- `QDRANT_URL=http://qdrant:6333` задаётся в `docker-compose.yml` (сеть между контейнерами)
- Дополнительная настройка не требуется

### Локальный запуск (без Docker)

**Вариант 1 — Qdrant как отдельный сервер**

1. Запустите Qdrant: `docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant`
2. В `.env` укажите: `QDRANT_URL=http://localhost:6333`
3. Либо в **Settings → General** задайте **Qdrant URL** = `http://localhost:6333` и сохраните

**Вариант 2 — file-режим (без отдельного сервера)**

1. В `.env`: `QDRANT_PATH=./qdrant_data` (путь к папке для хранения)
2. Либо в **Settings → General** задайте **Qdrant local path** = `./qdrant_data`
3. При заданном `QDRANT_PATH` URL игнорируется — Qdrant работает в файловом режиме

### Проверка

- Убедитесь, что Qdrant доступен: `curl http://localhost:6333/` (при URL-режиме)
- При ошибках индексации проверьте логи и настройки в General

---

## Настройка Ollama (LLM, embeddings, reranker)

При запуске в Docker контейнер приложения обращается к `localhost` внутри себя — до Ollama на хосте так не достучаться.

### Docker Compose

1. **Ollama как сервис Compose** (`docker compose --profile ollama up -d`):

   - В `.env` укажите: `KH_OLLAMA_URL=http://ollama:11434/v1/`
   - Либо в **Settings → General** задайте **Ollama API URL** = `http://ollama:11434/v1/`

2. **Ollama на хосте** (вне Docker):
   - Mac/Windows: `KH_OLLAMA_URL=http://host.docker.internal:11434/v1/`
   - Linux: `KH_OLLAMA_URL=http://172.17.0.1:11434/v1/` или IP хоста в сети

### Локальный запуск

- По умолчанию: `http://localhost:11434/v1/`

### Автообнаружение Ollama

В **Settings → Ollama servers** есть кнопка **«Найти Ollama на хосте»** — сканирует localhost, host.docker.internal, 172.17.0.1 и другие типичные адреса и автоматически добавляет найденные серверы. При первом запуске приложения поиск выполняется автоматически.

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
