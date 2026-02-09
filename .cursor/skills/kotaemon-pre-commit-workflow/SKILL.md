---
name: kotaemon-pre-commit-workflow
description: Проверка стиля и тестов перед коммитом. Использовать при проверке PR, запуске CI, перед push.
---

# Kotaemon Pre-commit Workflow

## Установка

```bash
pip install -e "libs/kotaemon[dev]"
pre-commit install
```

## Команды перед коммитом

**Проверка стиля (все файлы):**
```bash
pre-commit run --all-files
```

**Запуск тестов:**
```bash
cd libs/kotaemon
pytest
```

Или из корня:
```bash
pytest libs/kotaemon/tests/
```

## CI Cache

Если добавились новые зависимости или нужна чистая среда, добавь в тело коммита `[ignore cache]` — CI создаст свежее окружение.

## Инструменты pre-commit

- black, isort, flake8, autoflake, mypy, codespell
- prettier для markdown и yaml
- check-yaml, check-toml, end-of-file-fixer, trailing-whitespace и др.
