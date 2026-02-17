# Где хранятся данные Kotaemon и полный сброс

## Настройки из Web UI → .env

Все настройки (API-ключи, Qdrant, Ollama, TORCH_DEVICE, модели по умолчанию и т.д.) редактируются в **Settings → General**. При сохранении значения записываются в `.env` и `application_settings.json`. URL серверов Ollama также записывается в `.env` при добавлении/обнаружении в **Resources → Ollama servers**. Ручное редактирование `.env` не требуется.

Для применения изменений (TORCH_DEVICE, Qdrant, флаги индексов) нажмите **Restart** в Settings — приложение перезапустится автоматически.

## Расположение данных

### 1. Docker (volumes — переживают удаление проекта)

| Volume                   | Путь в контейнере          | Содержимое                |
| ------------------------ | -------------------------- | ------------------------- |
| `kotaemon_ktem_app_data` | `/app/ktem_app_data`       | Всё приложение            |
| `kotaemon_qdrant_data`   | `/qdrant/storage`          | Векторный индекс (Qdrant) |
| `kotaemon_postgres_data` | `/var/lib/postgresql/data` | PostgreSQL (если включён) |

**ktem_app_data** содержит:

- Все данные хранятся в **PostgreSQL** (пользователи, диалоги, индексы, настройки LLM/Embeddings/Rerankings).
- `user_data/files/` — загруженные файлы
- `user_data/docstore/` — LanceDB docstore
- `application_settings.json` — General (Ollama URL, GraphRAG, и т.д.)
- `markdown_cache_dir/`, `chunks_cache_dir/`, `zip_cache_dir*/`
- `huggingface/` — кэш моделей HF

### 2. Локальный запуск (без Docker)

- `./ktem_app_data/` — в корне проекта (рядом с flowsettings.py)
- Qdrant: `localhost:6333` или `QDRANT_PATH` для file-режима

---

## База данных: PostgreSQL

**PostgreSQL обязателен** для работы приложения. Используется для хранения пользователей, диалогов, индексов, настроек LLM/Embeddings/Rerankings.

### Настройка PostgreSQL

1. **Docker Compose** (рекомендуется):

   - Сервис `postgres` уже настроен в `docker-compose.yml` с оптимальными параметрами
   - `DATABASE_URL` задаётся автоматически или можно указать в `.env`
   - Сервис `app` автоматически зависит от `postgres`

2. **Локальный запуск** (без Docker):

   - Установите PostgreSQL с расширением `pgvector`
   - В `.env` задайте: `DATABASE_URL=postgresql://user:password@localhost:5432/kotaemon`

3. **Переменная окружения**:
   - Если `DATABASE_URL` не задан в `.env`, используется дефолт для Docker Compose: `postgresql://kotaemon:kotaemon@postgres:5432/kotaemon`

Таблицы создаются автоматически при первом запуске (SQLModel `create_all`). Миграции Alembic отключены по умолчанию (`KH_ENABLE_ALEMBIC = False`).

- **Document Types**: таблица `document_type` для пользовательских типов документов создаётся автоматически (при `KH_ENABLE_ALEMBIC=false`). Если используете Alembic (`KH_ENABLE_ALEMBIC=true`), выполните `alembic -c libs/ktem/alembic.ini upgrade head`.

**Автоматическая инициализация:** При первом запуске автоматически создаётся расширение `pgvector` (если используется векторное хранилище на PostgreSQL). Оптимальные параметры PostgreSQL применяются автоматически через `docker-compose.yml` или настройки сервера.

### Векторы в PostgreSQL (pgvector)

В той же БД можно хранить и векторные эмбеддинги (расширение **pgvector**). Тогда и реляционные данные, и векторы — в одном PostgreSQL.

1. Используйте образ с pgvector: в `docker-compose.yml` сервис `postgres` уже задан как `pgvector/pgvector:pg16`.
2. В `.env`: `DATABASE_URL=postgresql://...` и **`KH_VECTORSTORE_TYPE=pgvector`**.
3. Опционально: `PG_VECTOR_EMBED_DIM=1536` (или размерность вашей модели эмбеддингов).
4. **HNSW параметры** (оптимизированы по умолчанию, применяются автоматически, можно настроить в **Settings → General**):

   - **pgvector HNSW: m (connections per node)** = 16 — связи на узел (16-64, больше = точнее но медленнее)
   - **pgvector HNSW: ef_construction** = 64 — параметр построения индекса (64-200)
   - **pgvector HNSW: ef_search** = 40 — параметр поиска (40-200, больше = точнее но медленнее)

   Или через `.env`: `PG_VECTOR_HNSW_M=16`, `PG_VECTOR_HNSW_EF_CONSTRUCTION=64`, `PG_VECTOR_HNSW_EF_SEARCH=40`

**Автоматическая инициализация:** При первом запуске приложения автоматически:

- Создаётся расширение `pgvector` в PostgreSQL (если используется векторное хранилище на PostgreSQL)
- Применяются оптимальные HNSW параметры при создании векторных индексов
- Настраиваются оптимальные параметры PostgreSQL через `docker-compose.yml` (shared_buffers, work_mem и т.д.)

Дополнительная настройка не требуется — все оптимальные параметры применяются автоматически при установке.

Можно использовать **pgvector и Qdrant вместе**: в **Settings → General** выберите **Vector store** = **«Qdrant + pgvector (parallel, better quality)»**. Тогда при индексации данные пишутся в оба хранилища, а при поиске запрос идёт в оба параллельно и результаты объединяются по RRF (Reciprocal Rank Fusion) — приоритет на качество и скорость ответа.

### Оптимизация параметров векторизации

**HNSW для pgvector** (настройки в **Settings → General**, поля: **pgvector HNSW: m**, **pgvector HNSW: ef_construction**, **pgvector HNSW: ef_search**):

- **m** (connections per node): 16 — оптимально для большинства случаев. Увеличьте до 32-64 для большей точности (но медленнее и больше памяти).
- **ef_construction**: 64 — оптимально для баланса скорости построения и точности индекса.
- **ef_search**: 40 — оптимально для баланса скорости запросов и качества результатов. Увеличьте до 80-100 для максимальной точности.

Изменения применяются при следующей индексации документов (существующие индексы не перестраиваются автоматически).

### Document Types и document_links

- **Document Types** (Resources → Document Types): пользовательские типы документов, schema_def, генерация промптов через LLM. Таблица `document_type` создаётся автоматически.
- **document_links**: при индексации извлекаются связи между документами (счёт → контракт и т.п.) и сохраняются в `Source.note["document_links"]`.
- **LightRAG + document_links**: при использовании LightRAG (`USE_LIGHTRAG=true`) связи автоматически добавляются в граф как рёбра между сущностями. Для LightRAG: `pip install git+https://github.com/HKUDS/LightRAG.git` (Docker-образ main-full уже содержит LightRAG).

**PostgreSQL** (в `docker-compose.yml` уже настроены оптимальные параметры):

- `shared_buffers=256MB` — кэш данных (25% RAM для небольших серверов)
- `effective_cache_size=1GB` — для планировщика запросов
- `maintenance_work_mem=64MB` — для построения индексов (включая HNSW)
- `work_mem=16MB` — для сортировок и хеш-таблиц
- `random_page_cost=1.1` — оптимизировано для SSD
- `effective_io_concurrency=200` — для параллельного I/O

**Connection pooling** (SQLAlchemy, автоматически для PostgreSQL):

- `pool_size=10` — базовый пул соединений
- `max_overflow=20` — дополнительные соединения при нагрузке
- `pool_recycle=3600` — пересоздание соединений каждый час

**Composite (Qdrant + pgvector)**:

- Запрашивает `top_k * 4` кандидатов из каждого хранилища (до 100) для лучшего качества RRF объединения.
- RRF использует `k=60` для сглаживания рангов (оптимально для 2-3 хранилищ).

**Qdrant** (настройки в Settings → General):

- **Hybrid search**: включите для лучшего качества (dense + sparse векторы). Требует `QDRANT_FASTEMBED_SPARSE_MODEL` (например, `Qdrant/bm25`).
- Коллекции создаются автоматически с оптимальными параметрами (COSINE distance, HNSW индексы).
- Для продакшена рекомендуется Qdrant Cloud или отдельный сервер с настройками производительности.

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

### Предупреждение «Api key is used with an insecure connection»

Если задан **Qdrant API key** и **Qdrant URL** начинается с `http://` (без TLS), LlamaIndex выводит это предупреждение. В текущей конфигурации при использовании `http://` API key не передаётся (для локального Qdrant ключ не нужен). Для Qdrant Cloud используйте **https://** и задайте API key в Settings → General.

### Ошибка «Vector dimension error: expected dim: X, got Y»

Размерность эмбеддингов при индексации и при поиске должна совпадать. Ошибка означает, что:

- Коллекция Qdrant создана с одной моделью эмбеддингов (например, 4096 dim)
- Текущая модель эмбеддингов в Retrieval settings даёт другую размерность (например, 768 dim)

**Что сделать:** либо переиндексировать все документы с текущей моделью эмбеддингов, либо задать в **Retrieval settings** ту же модель, что использовалась при индексации.

**Полный сброс и переиндексация:**

```bash
docker compose down -v
docker volume rm kotaemon_ktem_app_data kotaemon_qdrant_data kotaemon_postgres_data 2>/dev/null || true
docker compose up -d
```

После этого заново загрузите и проиндексируйте документы. Если используете PostgreSQL, volume `kotaemon_postgres_data` удалит все данные БД.

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
docker volume rm kotaemon_ktem_app_data kotaemon_qdrant_data kotaemon_postgres_data 2>/dev/null || true
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
docker volume rm kotaemon_ktem_app_data kotaemon_qdrant_data kotaemon_postgres_data

# Запустить заново
docker compose up -d
```

После этого данные обнуляются, приложение стартует как при первом запуске.
