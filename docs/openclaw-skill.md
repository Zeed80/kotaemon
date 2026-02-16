# OpenClaw Skill: Kotaemon RAG

## Описание

**Kotaemon RAG** — skill для OpenClaw и внешних агентов. Позволяет выполнять запросы к документам, проиндексированным в Kotaemon.

## Формат вызова

### POST /api/v1/query

Запрос к RAG по вопросу.

**Заголовки:**
- `Authorization: Bearer <API_SECRET_KEY>` или `X-API-Key: <API_SECRET_KEY>` — если задан `API_SECRET_KEY` в `.env`

**Тело (JSON):**
```json
{
  "question": "Сумма счёта?",
  "file_ids": ["file-uuid-1"],
  "index_ids": [1, 2]
}
```

| Поле       | Тип         | Обязательно | Описание                                   |
|-----------|--------------|-------------|--------------------------------------------|
| question  | string       | да          | Вопрос к документам                        |
| file_ids  | string[]     | нет         | Ограничить поиск указанными файлами        |
| index_ids | integer[]    | нет         | Индексы для поиска (по умолчанию все)      |

**Ответ:**
```json
{
  "answer": "Сумма счёта составляет 1500 руб.",
  "sources": "[1] Документ.pdf, стр. 2..."
}
```

## Дополнительные эндпоинты

### POST /api/v1/upload

Загрузка файлов и постановка в очередь индексации.

**Формат:** `multipart/form-data`

- `files` — файлы
- `target_indices` — список id индексов через запятую (опционально)

**Ответ:** `{"job_id": "abc123"}`

### GET /api/v1/jobs/{job_id}

Статус задачи индексации.

**Ответ:** `{"job_id": "...", "status": "done", "progress": 1.0, ...}`

## OpenAPI spec

Спецификация генерируется автоматически из FastAPI:
- `/openapi.json` — JSON
- `/docs` — Swagger UI (если Gradio смонтирован через FastAPI)

Запуск с API: `uvicorn app_fastapi:app --host 0.0.0.0 --port 7860`

## Проверка API

```bash
# Проверить маршруты (без запуска сервера)
python scripts/test_api.py --routes-only

# Проверить доступность эндпоинтов (сервер должен быть запущен)
python scripts/test_api.py http://localhost:7860
```

## Настройка

1. Установите `API_SECRET_KEY` в `.env` для защиты API
2. При пустом ключе — доступ без аутентификации (для локальной разработки)
