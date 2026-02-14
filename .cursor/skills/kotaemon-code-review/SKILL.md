---
name: kotaemon-code-review
description: Чеклист для ревью кода kotaemon. Использовать при code review, проверке PR.
---

# Kotaemon Code Review

## Checklist

### BaseComponent Pattern

- [ ] Компоненты наследуют `BaseComponent`
- [ ] Param и Node объявлены корректно
- [ ] Метод `run()` реализован с правильной сигнатурой
- [ ] Входные типы допускаются разные, выходной — единый

### Стиль кода

- [ ] black, isort, flake8 пройдены
- [ ] mypy без ошибок (--check-untyped-defs, --ignore-missing-imports)
- [ ] Нет неиспользуемых импортов (autoflake)

### Тесты

- [ ] Новые core-функции покрыты тестами
- [ ] `pytest libs/kotaemon/tests/` проходит

### PR Checklist (из шаблона)

- [ ] Self-review выполнен
- [ ] Есть ссылка на issue/bug report
- [ ] Сложные места прокомментированы
- [ ] Функциональность задокументирована

## Формат фидбека

- **Critical**: Обязательно исправить перед merge
- **Suggestion**: Рекомендуется доработать
- **Nice to have**: Опциональное улучшение
