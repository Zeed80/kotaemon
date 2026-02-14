# План перехода на SearXNG вместо Jina Search

## Цель

Заменить платный Jina Search на self-hosted SearXNG для web search: локальность, приватность, без API-ключей к сторонним сервисам.

## Текущее состояние

- **KH_WEB_SEARCH_BACKEND**: Tavily (если ключ) → Jina (fallback, требует JINA_API_KEY)
- Оба варианта — облачные API, данные уходят на сторонние сервисы

## Целевое состояние

- **KH_WEB_SEARCH_BACKEND**: Tavily (опционально, если ключ) → **SearXNG** (default fallback)
- SearXNG — self-hosted, без API-ключей, запросы только к своему экземпляру

## Фаза 1: SearXNG retriever

Создать `kotaemon.indices.retrievers.searxng_web_search.WebSearch`:

- Запрос: `GET {SEARXNG_URL}/search?q={query}&format=json`
- Парсинг JSON: `results[]` → `url`, `title`, `content`
- Формат выхода: `RetrievedDocument` (как Tavily/Jina)
- Нет API-ключа
- `requests` уже в зависимостях

## Фаза 2: Конфигурация

- **flowsettings_config.py**: `SEARXNG_URL: str = "http://localhost:8080"`
- **flowsettings.py**: логика fallback:
  - `TAVILY_API_KEY` → Tavily
  - иначе → SearXNG (по умолчанию для приватности)

## Фаза 3: Docker

- Добавить сервис `searxng` в docker-compose.yml
- Официальный образ: `searxng/searxng`
- Порт 8080
- Для app: `SEARXNG_URL: http://searxng:8080`, `depends_on: [searxng]`

## Фаза 4: Документация

- README: описание SEARXNG_URL, приватность, docker compose
- Убрать/сократить упоминания Jina для web search

## Порядок работ

1. Фаза 1 — retriever
2. Фаза 2 — конфиг
3. Фаза 3 — Docker
4. Фаза 4 — README
