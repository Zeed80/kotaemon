# Полная инспекция качества, совместимости и актуальности — Kotaemon

Дата: 2026-02-10  
Репозиторий: `J:/Project/kotaemon`

## 1) Инвентаризация компонентов и инструментов

### 1.1 Backend и ядро
- `libs/kotaemon` — core-библиотека (LLM, embeddings, loaders, indices, storages, promptui).
- `libs/ktem` — приложение (Gradio UI, страницы, reasoning, индексирование, db).
- Точки входа: `app.py`, `launch.sh`, `libs/kotaemon/kotaemon/cli.py`.

### 1.2 UI/Frontend слой
- UI реализован на Gradio (без отдельного npm frontend).
- Статические ассеты: `libs/ktem/ktem/assets/css`, `libs/ktem/ktem/assets/js`, `libs/ktem/ktem/assets/prebuilt`.
- Внешние клиентские зависимости подключаются через CDN в `libs/ktem/ktem/app.py`.

### 1.3 Качество и тесты
- Конфигурация хуков: `.pre-commit-config.yaml`.
- CI workflows: `.github/workflows/style-check.yaml`, `.github/workflows/unit-test.yaml`, `.github/workflows/pr-lint.yaml`.
- Тесты ядра: `libs/kotaemon/tests`.
- Тесты приложения: `libs/ktem/ktem_tests` (требуют валидации актуальности).

### 1.4 Поставка и инфраструктура
- Контейнеризация: `Dockerfile`, `docker-compose.yml`, `.dockerignore`.
- Релизы/образы: `.github/workflows/build-push-docker.yaml`, `.github/workflows/auto-bump-and-release.yaml`.
- Документация процессов: `CONTRIBUTING.md`, `docs/development/contributing.md`, `mkdocs.yml`.

### 1.5 Набор инструментов качества (факт)
- `black`, `isort`, `flake8`, `autoflake`, `ruff-check --fix`, `mypy`, `codespell`, `prettier (md/yaml)` через pre-commit.
- CI style-check запускает pre-commit.
- CI unit-test запускает pytest только в `libs/kotaemon`.
- PR lint проверяет заголовок PR; job `commitlint` присутствует, но отключен.

## 2) Первичный risk-register (до выполнения проверок)

| ID | Область | Риск | Доказательство | Критичность |
|---|---|---|---|---|
| R1 | Тесты/CI | Тесты `ktem` не интегрированы в основной CI | `unit-test.yaml` запускает только `libs/kotaemon` | High |
| R2 | Тесты | Потенциально устаревшие тесты в `ktem_tests` | `libs/ktem/ktem_tests/test_qa.py`: `from index import ReaderIndexingPipeline` | High |
| R3 | Совместимость UI | Использование чувствительных внутренностей Gradio | `ChatInterface`, `special_args`, `get_component_instance`, `FileData`, `NamedString` | High |
| R4 | Надежность UI | Зависимость от внешних CDN без fallback/self-host policy | `libs/ktem/ktem/app.py` (skypack/cdnjs/jsdelivr) | Medium |
| R5 | Процесс качества | Часть commit-policy не enforce в CI | `.github/workflows/pr-lint.yaml` (`commitlint` с `if: false`) | Medium |
| R6 | Кроссплатформенность | Windows исключен из test matrix | `unit-test.yaml` windows job закомментирован | Medium |
| R7 | Security pipeline | Нет обязательного dependency/image/SAST сканирования в CI | отсутствуют workflow для `pip-audit`/Trivy/bandit/CodeQL | High |
| R8 | Метрики качества | Coverage gate отсутствует | в CI не запускается coverage-порог | Medium |

## 3) Методика проверки (по плану)
- A: статика и базовое качество.
- B: тесты и покрытие.
- C: runtime/UI smoke и совместимость.
- D: актуальность и безопасность зависимостей.
- E: CI/CD и release hygiene.
- F: документация и процессное соответствие.

## 4) Статус выполнения
- [x] Инвентаризация и первичный risk-register.
- [ ] Статика/тесты/smoke.
- [ ] Security/dependency/CI аудит.
- [ ] Финальный consolidated report и roadmap.

## 5) Результаты проверок A/B/C (факт)

### A. Статика и базовое качество

1) `python -m pre_commit run --all-files`  
- **Статус:** Fail  
- **Факт:** конфигурационный сбой pre-commit:
  - `[ERROR] ruff-check is not present in repository https://github.com/astral-sh/ruff-pre-commit`
- **Вывод:** текущий локальный quality-gate не воспроизводится в этом окружении из-за несоответствия hook id/rev.

2) `python -m mypy kotaemon` (в `libs/kotaemon`)  
- **Статус:** Fail  
- **Факт:** `No module named mypy`.
- **Вывод:** типизация не может быть запущена локально без установки dev toolchain.

### B. Тестовая стратегия и покрытие

1) `python -m pytest` (в `libs/kotaemon`)  
- **Статус:** Fail (ошибки на этапе collection)  
- **Факты:**
  - `ModuleNotFoundError: No module named 'elastic_transport'` (`tests/test_docstores.py`)
  - `ImportError: cannot import name 'HfFolder' from 'huggingface_hub'` через импорт `gradio` (`tests/test_promptui.py`)
- **Вывод:** окружение не соответствует ожидаемому dependency set; есть несовместимость `gradio`/`huggingface_hub`.

2) `python -m pytest` (в `libs/ktem`)  
- **Статус:** Fail (ошибка на этапе collection)  
- **Факт:** `ModuleNotFoundError: No module named 'index'` в `ktem_tests/test_qa.py`.
- **Вывод:** тестовый модуль содержит устаревший импорт.

3) Coverage  
- **Статус:** Not met  
- **Факт:** запуск с coverage-гейтом в CI не настроен; локально коллекция тестов падает до выполнения.

### C. Совместимость runtime/UI (smoke)

1) `python -c "import app"` (root)  
- **Статус:** Fail  
- **Факт:** `ModuleNotFoundError: No module named 'ktem'` без настроенного PYTHONPATH/editable install.

2) `python -c "import app"` с `PYTHONPATH=libs/ktem;libs/kotaemon`  
- **Статус:** Fail  
- **Факт:** повторяется `ImportError: cannot import name 'HfFolder' from 'huggingface_hub'` через `gradio`.

3) `python -c "from kotaemon.contribs.promptui.config import export_pipeline_to_config"`  
- **Статус:** Fail  
- **Факт:** та же несовместимость `gradio` ↔ `huggingface_hub`.

4) Локальная матрица Python/OS  
- `py -0p` показывает только `Python 3.11.4` на Windows.
- Полная локальная матрица `3.10/3.11` и Linux недоступна; Linux покрывается CI-конфигом, Windows в CI отключен.

## 6) Результаты проверок D/E/F (факт)

### D. Актуальность и безопасность зависимостей

1) Outdated snapshot (`python -m pip list --outdated --format=json`)  
- **Статус:** Issues found  
- **Факты (срез):**
  - `gradio 4.44.1 -> 6.5.1`
  - `huggingface_hub 1.3.3 -> 1.4.1`
  - `fastapi 0.112.1 -> 0.128.6`
  - `starlette 0.38.6 -> 0.52.1`
  - `pypdf 4.2.0 -> 6.7.0`
- **Вывод:** стек содержит большой разрыв версий; для части зависимостей это major migration.

2) Vulnerability scan (`python -m pip_audit -f json`)  
- **Статус:** Fail (vulns present)  
- **Факты:**
  - `deps_total=423`
  - `deps_with_vulns=17`
  - `vuln_total=59`
  - Топ по количеству уязвимостей:
    - `gradio 4.44.1` — 16
    - `aiohttp 3.13.2` — 8
    - `pypdf 4.2.0` — 7
    - `llama-index 0.10.68` — 6
  - Примеры:
    - `gradio`: `PYSEC-2024-213` (fix: `5.0.0`)
    - `aiohttp`: `CVE-2025-69223` (fix: `3.13.3`)
    - `pypdf`: `CVE-2025-55197` (fix: `6.0.0`)
    - `starlette`: `CVE-2024-47874` (fix: `0.40.0`)

3) Container/image scanning readiness  
- **Статус:** Fail  
- **Факты:** `trivy` не установлен локально; в workflow нет отдельного шага image scan.

### E. CI/CD и release hygiene

1) Полнота CI  
- **Статус:** Partial  
- **Факты:**
  - `style-check.yaml`: push/PR в `main` и `develop`.
  - `unit-test.yaml`: push/PR только в `main`; тестирует только `libs/kotaemon`.
  - Windows job в `unit-test.yaml` закомментирован.
  - `pr-lint.yaml`: commitlint job выключен (`if: false`).

2) Release pipeline  
- **Статус:** Risk accepted / requires hardening  
- **Факты:**
  - Есть автотегирование и релиз-архив.
  - Есть сборка и push Docker образов (`lite/full/ollama`).
  - Нет обязательного security gate перед публикацией образов.

### F. Документация и процессное соответствие

1) Соответствие contributing docs текущему CI  
- **Статус:** Partial  
- **Факт:** в `docs/development/contributing.md` секция cache ссылается на `__init__.py`/`setup.py`, тогда как CI использует `setuptools-git-versioning` и ключи в `unit-test.yaml`.

2) Docs CI  
- **Статус:** Gap  
- **Факт:** нет workflow, который собирает `mkdocs` и валидирует docs как обязательный quality gate.

## 7) Матрица совместимости (по результатам инспекции)

| Область | Целевое/ожидаемое | Фактическое | Статус |
|---|---|---|---|
| Python | 3.10 и 3.11 | локально только 3.11 | Partial |
| OS | Linux + Windows | CI: Linux only, Windows disabled | Fail |
| Gradio API | `>=4.31,<5` с рабочим runtime | `4.44.1` + несовместимость с `huggingface_hub 1.3.3` (`HfFolder`) | Fail |
| PromptUI | Импорт/базовый запуск | ломается на импорте gradio stack | Fail |
| Core tests | `libs/kotaemon/tests` green | collection errors (deps mismatch) | Fail |
| App tests | `libs/ktem/ktem_tests` green | collection error (`from index import ...`) | Fail |
| Security scan | dependency + image scan в CI | dependency scan отсутствует в CI, image scan отсутствует | Fail |
| Commit policy | conventional commits enforced | PR title enforced, commitlint job disabled | Partial |
| Coverage | измерение + порог в CI | отсутствует coverage gate | Fail |

## 8) Приоритизированный roadmap исправлений

### Quick Wins (1-2 недели)
1. Починить pre-commit конфиг для `ruff` hook (воспроизводимый локальный gate).
2. Исправить `libs/ktem/ktem_tests/test_qa.py` (устаревший импорт) и включить `ktem_tests` в CI.
3. Включить `commitlint` job или официально удалить его из workflow.
4. Добавить отдельный CI job для `pip-audit` с fail на High/Critical.
5. Добавить docs-check job (`mkdocs build --strict`).

### Mid-term (1-2 спринта)
1. Восстановить/добавить Windows job в `unit-test.yaml`.
2. Ввести coverage сбор и порог (например, по `libs/kotaemon` + базовые `ktem` smoke).
3. Устранить несовместимость `gradio`/`huggingface_hub` через согласованный dependency pin-set.
4. Добавить container scan (Trivy/Grype) в pipeline публикации образов.

### Hardening (квартал)
1. Сформировать стратегию major-upgrade для `gradio`, `langchain`, `llama-index`, `pypdf` с поэтапной миграцией.
2. Сократить дублирование линтеров (`flake8` vs `ruff`) до единой политики.
3. Ввести security baseline: SAST (bandit/semgrep/CodeQL), SBOM и регулярный dependency refresh cycle.

## 9) Обновленный статус выполнения
- [x] Инвентаризация и первичный risk-register.
- [x] Статика/тесты/smoke.
- [x] Security/dependency/CI аудит.
- [ ] Финальный consolidated report и roadmap.

## 10) Executive summary

- Проект имеет зрелую базу автоматизации (pre-commit, unit tests, Docker build/release), но текущий quality/security контур неполный.
- Основные блокеры качества: неработающий локальный pre-commit gate, падающие тесты на collection, неинтегрированные `ktem` тесты, отсутствие coverage gate.
- Основные блокеры совместимости: runtime-конфликт `gradio` и `huggingface_hub` (`HfFolder`), отключенная Windows-проверка, чувствительные внутренние API Gradio в PromptUI.
- Основные блокеры безопасности: `pip-audit` выявил 59 уязвимостей в 17 пакетах, а CI не содержит обязательного dependency/image scanning.
- Ключевая рекомендация: сначала стабилизировать воспроизводимость качества (A/B/C), затем ввести обязательные security gates (D/E), после — планировать controlled major upgrades.

## 11) Детализированный issue list (приоритет, effort, владелец)

| Приоритет | Область | Симптом | Доказательство | Риск | Рекомендация | Effort | Владелец |
|---|---|---|---|---|---|---|---|
| Critical | Runtime | `gradio` импорт падает из-за `HfFolder` | импорт `app` и PromptUI падает | Неработоспособность UI/тестов | Зафиксировать совместимый pin-set `gradio`/`huggingface_hub` и прогнать smoke | M | Backend/UI |
| High | Test infra | `ktem_tests` падают на `from index import ...` | `libs/ktem/ktem_tests/test_qa.py` | Нет валидного тестового контура приложения | Обновить импорт на актуальный модульный путь | S | Backend/UI |
| High | CI scope | `ktem` тесты не запускаются в CI | `unit-test.yaml` тестирует только `libs/kotaemon` | Регрессии в app слое не ловятся | Добавить job для `libs/ktem/ktem_tests` | S | CI |
| High | Security | Нет обязательного dependency scanning в CI | отсутствует job `pip-audit/safety` | Уязвимости попадают в main/release | Добавить security job с порогами fail | S | Security/CI |
| High | Security | Нет image scan для Docker release | в build workflow нет Trivy/Grype | Публикация уязвимых образов | Добавить scan step до push/release | M | DevOps |
| Medium | Quality gate | pre-commit не запускается локально | ошибка `ruff-check is not present` | Снижение доверия к локальной проверке | Синхронизировать hook id/rev (или autoupdate + фиксация) | S | Backend |
| Medium | Coverage | Нет coverage gate | отсутствует в CI | Скрытые регрессии по неочевидным веткам | Ввести `pytest --cov` и минимальный порог | M | QA/CI |
| Medium | Cross-platform | Windows job отключен | закомментирован в `unit-test.yaml` | Регрессии Windows обнаруживаются поздно | Вернуть Windows в matrix (хотя бы smoke subset) | M | CI |
| Medium | Process | Commit policy частично выключен | `commitlint` job `if: false` | Непоследовательная история commit message | Включить или удалить неиспользуемый job | S | Maintainers |
| Medium | Docs | Contributing cache section устарел | упоминание `__init__.py/setup.py` vs `setuptools-git-versioning` | Ошибки contributor workflow | Актуализировать docs под текущий CI | S | Docs |

## 12) Финальный статус
- [x] Инвентаризация и первичный risk-register.
- [x] Статика/тесты/smoke.
- [x] Security/dependency/CI аудит.
- [x] Финальный consolidated report, матрица совместимости и roadmap.

## 13) Реализация плана исправлений

В рамках реализации remediation-плана выполнены ключевые изменения:

- Stage 1: восстановлен запуск quality-gate:
  - исправлен `ruff` hook в `.pre-commit-config.yaml` (`ruff-check` -> `ruff`);
  - для `isort` убран жесткий `python3.10` в пользу `python3`;
  - добавлено исключение `.venv_check` из pre-commit-обхода.
- Stage 2: зафиксирована runtime-совместимость по зависимости:
  - добавлен pin `huggingface-hub<1.0` в `libs/kotaemon/pyproject.toml` и `libs/ktem/pyproject.toml`;
  - `PromptUI` smoke import проходит;
  - app smoke переведен на безопасный `App()` ctor (без `launch()`).
- Stage 3: стабилизирован `ktem` тест:
  - переписан `libs/ktem/ktem_tests/test_qa.py` под текущую архитектуру;
  - добавлен bootstrap `THEFLOW_SETTINGS_MODULE=flowsettings` для корректной загрузки настроек;
  - тест-модуль проходит (`2 passed`).
- Stage 4: усилен CI:
  - `unit-test` дополнен запуском `ktem_tests`;
  - добавлен coverage gate для `kotaemon`;
  - добавлен `windows-smoke` job;
  - в `pr-lint` включена проверка commit messages (удален `if: false`).
- Stage 5: добавлены security gates:
  - новый workflow `.github/workflows/security-check.yaml` с `pip-audit`;
  - в Docker publish workflow добавлен Trivy scan перед push.
- Stage 6: актуализированы docs/process:
  - обновлены `CONTRIBUTING.md` и `docs/development/contributing.md`;
  - добавлен docs CI `.github/workflows/docs-check.yaml` (`mkdocs build --strict`).
- Stage 7: добавлен hardening playbook:
  - `docs/development/quality-hardening-playbook.md`;
  - добавлен пункт в `mkdocs.yml`.
