# AGENTS.md — Руководство для AI в Kotaemon

## Язык

- Всегда общаться на **русском языке**.

## MCP

- **context7**: Использовать для актуальной документации библиотек и примеров.
- **Magic MCP**: Использовать при разработке frontend и Gradio UI.

## Код

- **Не делать заглушки** — писать сразу полный, рабочий код.
- При изменениях **проверять зависимые места** и вносить правки везде, где нужно.
- Разработка на **последних поддерживаемых версиях** зависимостей (см. pyproject.toml, requirements.txt).

## Правила и Skills

- Соблюдать правила в `.cursor/rules/`.
- Применять skills из `.cursor/skills/` по контексту:
  - `kotaemon-component-development` — создание компонентов
  - `kotaemon-pre-commit-workflow` — проверка перед коммитом
  - `kotaemon-code-review` — ревью кода и PR
  - `kotaemon-rag-pipeline` — reasoning, indexing, retrieval

## Конвенции

- Python: black, isort, flake8, mypy (см. `.pre-commit-config.yaml`).
- Коммиты: Angular convention — `type(scope): subject` (см. `.commitlintrc`).
- Компоненты: BaseComponent pattern (см. `docs/development/create-a-component.md`).
