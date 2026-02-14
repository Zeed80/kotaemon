#!/usr/bin/env bash
# Kotaemon — скрипт установки и развёртывания
# Использование: ./install.sh [--docker | --local] [--no-pdfjs] [--no-launch]
# По умолчанию: локальная установка (Python + venv), с загрузкой PDF.js и запуском приложения.

set -euo pipefail
[[ -n "${DEBUG:-}" ]] && set -x

# --- Константы и пути ---
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${__dir}"
VENV_DIR="${REPO_ROOT}/.venv"
PDFJS_PREBUILT_DIR="${REPO_ROOT}/libs/ktem/ktem/assets/prebuilt"
PDFJS_VERSION="4.0.379"
PDFJS_DIST_NAME="pdfjs-${PDFJS_VERSION}-dist"
ENV_EXAMPLE="${REPO_ROOT}/.env.example"
ENV_FILE="${REPO_ROOT}/.env"

# Режимы установки
MODE_LOCAL="local"
MODE_DOCKER="docker"
INSTALL_MODE="${MODE_LOCAL}"
SKIP_PDFJS=false
SKIP_LAUNCH=false

# --- Подсветка вывода ---
print_step() {
    echo ""
    echo "******************************************************"
    echo "$1"
    echo "******************************************************"
    echo ""
}

print_ok() {
    echo "[OK] $1"
}

print_warn() {
    echo "[!] $1" >&2
}

print_err() {
    echo "[ERROR] $1" >&2
}

# --- Справка ---
usage() {
    cat <<EOF
Kotaemon — установка и развёртывание

Использование:
  $0 [OPTIONS]

Режимы:
  --local   Установка в локальное окружение Python (по умолчанию):
            создаётся .venv, ставятся зависимости, при необходимости .env из .env.example.
  --docker  Развёртывание через Docker Compose:
            образ собирается и запускается в фоне, данные в volume.

Опции:
  --no-pdfjs   Не загружать PDF.js (локальная установка). Просмотр PDF в браузере будет недоступен.
  --no-launch  Не запускать приложение после установки (локальная установка).
  --help       Показать эту справку.

Примеры:
  $0                    # Локально: venv + зависимости + .env + PDF.js + запуск
  $0 --no-launch        # Только установка, без запуска
  $0 --docker           # Docker Compose: сборка и запуск контейнера
  $0 --docker --no-launch   # Только сборка образа (запуск: docker compose up -d)

После установки:
  Локально:  python app.py   (или активируйте .venv и запустите app.py)
  Docker:    http://localhost:7860   (порт настраивается в .env: KOTAEMON_PORT)

GPU (Unstructured/Docling):
  Локально:  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  Docker:    GPU включён по умолчанию; для CPU: docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d
  Требуется NVIDIA GPU и NVIDIA Container Toolkit для Docker.
EOF
}

# --- Разбор аргументов ---
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
        --docker)
            INSTALL_MODE="${MODE_DOCKER}"
            shift
            ;;
        --local)
            INSTALL_MODE="${MODE_LOCAL}"
            shift
            ;;
        --no-pdfjs)
            SKIP_PDFJS=true
            shift
            ;;
        --no-launch)
            SKIP_LAUNCH=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            print_err "Неизвестный аргумент: $1"
            usage
            exit 1
            ;;
        esac
    done
}

# --- Проверка окружения для локальной установки ---
check_local_env() {
    local py_cmd=""
    if command -v python3 &>/dev/null; then
        py_cmd="python3"
    elif command -v python &>/dev/null; then
        py_cmd="python"
    else
        print_err "Не найден Python. Установите Python 3.10+ или используйте: $0 --docker"
        exit 1
    fi

    local version
    version=$("$py_cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
    if [[ -z "${version}" ]]; then
        print_err "Не удалось определить версию Python. Требуется Python 3.10+."
        exit 1
    fi
    local major minor
    major="${version%%.*}"
    minor="${version#*.}"
    minor="${minor%%.*}"
    if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 10 ]]; }; then
        print_err "Требуется Python 3.10+, обнаружено: $version. Используйте --docker или обновите Python."
        exit 1
    fi
    print_ok "Python $version"
    echo "$py_cmd"
}

# --- Проверка путей без пробелов (избегаем проблем с pip/conda) ---
check_path_no_spaces() {
    if [[ "$REPO_ROOT" =~ [[:space:]] ]]; then
        print_err "Путь к репозиторию содержит пробелы, это может вызвать сбои. Рекомендуется путь без пробелов."
        exit 1
    fi
}

# --- Создание и активация venv ---
setup_venv() {
    local py_cmd="$1"
    if [[ -d "${VENV_DIR}" ]]; then
        print_ok "Виртуальное окружение уже есть: ${VENV_DIR}"
        return
    fi
    print_step "Создание виртуального окружения в ${VENV_DIR}"
    "$py_cmd" -m venv "${VENV_DIR}"
    print_ok "Виртуальное окружение создано"
}

# --- Активация venv (вывод команды для подсказки) ---
venv_activate_cmd() {
    echo "source ${VENV_DIR}/bin/activate"
}

# --- Установка зависимостей (локально) ---
install_local_deps() {
    local py_cmd="$1"
    local pip_cmd="${VENV_DIR}/bin/pip"
    local need_install=false

    if [[ -d "${VENV_DIR}" ]]; then
        pip_cmd="${VENV_DIR}/bin/pip"
    else
        pip_cmd="$py_cmd -m pip"
    fi

    if "${pip_cmd}" list 2>/dev/null | grep -q "kotaemon"; then
        print_ok "Пакеты kotaemon/ktem уже установлены"
    else
        need_install=true
    fi

    if [[ "${need_install}" == "true" ]]; then
        print_step "Установка зависимостей (kotaemon, ktem)"
        if [[ -d "${VENV_DIR}" ]]; then
            "${VENV_DIR}/bin/pip" install -e "libs/kotaemon[all]" -e "libs/ktem"
        else
            "$py_cmd" -m pip install -e "libs/kotaemon[all]" -e "libs/ktem"
        fi
        print_ok "Зависимости установлены"
    fi
}

# --- Настройка .env ---
setup_env_file() {
    if [[ -f "${ENV_FILE}" ]]; then
        print_ok "Файл .env уже существует"
        return
    fi
    if [[ ! -f "${ENV_EXAMPLE}" ]]; then
        print_warn "Файл .env.example не найден. Создайте .env вручную с переменными окружения."
        return
    fi
    print_step "Создание .env из .env.example"
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    print_ok "Создан ${ENV_FILE}. Заполните API-ключи и при необходимости измените настройки."
}

# --- Загрузка PDF.js ---
setup_pdfjs() {
    if [[ "${SKIP_PDFJS}" == "true" ]]; then
        print_ok "Пропуск загрузки PDF.js (--no-pdfjs)"
        return
    fi
    local target_dir="${PDFJS_PREBUILT_DIR}/${PDFJS_DIST_NAME}"
    if [[ -d "${target_dir}" ]]; then
        print_ok "PDF.js уже загружен: ${target_dir}"
        return
    fi
    print_step "Загрузка PDF.js для просмотра документов в браузере"
    if [[ -f "${REPO_ROOT}/scripts/download_pdfjs.sh" ]]; then
        mkdir -p "${PDFJS_PREBUILT_DIR}"
        bash "${REPO_ROOT}/scripts/download_pdfjs.sh" "${target_dir}"
    else
        print_warn "Скрипт scripts/download_pdfjs.sh не найден. PDF.js можно скачать вручную в ${target_dir}"
        return
    fi
    print_ok "PDF.js установлен"
}

# --- Запуск приложения (локально) ---
launch_local() {
    if [[ "${SKIP_LAUNCH}" == "true" ]]; then
        print_ok "Запуск приложения пропущен (--no-launch)"
        return
    fi
    print_step "Запуск веб-интерфейса"
    local py_app="${VENV_DIR}/bin/python"
    if [[ ! -d "${VENV_DIR}" ]]; then
        py_app="python3"
        command -v python3 &>/dev/null || py_app="python"
    fi
    export PDFJS_PREBUILT_DIR="${PDFJS_PREBUILT_DIR}/${PDFJS_DIST_NAME}"
    (cd "${REPO_ROOT}" && "${py_app}" app.py) || {
        print_err "Запуск завершился с ошибкой."
        exit 1
    }
}

# --- Локальная установка (полный путь) ---
run_local_install() {
    local py_cmd
    py_cmd=$(check_local_env)
    check_path_no_spaces
    cd "${REPO_ROOT}"

    setup_venv "$py_cmd"
    install_local_deps "$py_cmd"
    setup_env_file
    setup_pdfjs

    print_step "Локальная установка завершена"
    echo "  Виртуальное окружение: ${VENV_DIR}"
    echo "  Активация: $(venv_activate_cmd)"
    echo "  Запуск:    python app.py (из корня репозитория после активации venv)"
    echo "  Настройки: большинство параметров можно изменить в веб-интерфейсе: Settings → General."
    echo ""

    launch_local
}

# --- Проверка Docker и Docker Compose ---
check_docker() {
    if ! command -v docker &>/dev/null; then
        print_err "Docker не найден. Установите Docker или используйте: $0 --local"
        exit 1
    fi
    if ! docker compose version &>/dev/null && ! docker-compose version &>/dev/null; then
        print_err "Docker Compose не найден. Установите Docker Compose (или плагин docker compose)."
        exit 1
    fi
    print_ok "Docker и Docker Compose доступны"
}

# --- Развёртывание через Docker ---
run_docker_install() {
    check_docker
    cd "${REPO_ROOT}"

    if [[ ! -f "${ENV_FILE}" ]] && [[ -f "${ENV_EXAMPLE}" ]]; then
        print_step "Создание .env из .env.example"
        cp "${ENV_EXAMPLE}" "${ENV_FILE}"
        print_ok "Создан ${ENV_FILE}. При необходимости отредактируйте API-ключи."
    fi

    print_step "Сборка и запуск контейнера (Docker Compose)"
    docker compose build --ssh default
    docker compose up -d
    print_ok "Контейнер запущен."
    echo ""
    echo "  Интерфейс:  http://localhost:${KOTAEMON_PORT:-7860}"
    echo "  Обновление: ./scripts/docker-update.sh"
    echo "  Логи:       docker compose logs -f"
    echo "  Остановка:  docker compose down"
    echo "  Ollama отдельным контейнером: docker compose --profile ollama up -d"
    echo ""
}

# --- Точка входа ---
main() {
    parse_args "$@"

    case "${INSTALL_MODE}" in
    "${MODE_DOCKER}")
        run_docker_install
        ;;
    "${MODE_LOCAL}")
        run_local_install
        ;;
    *)
        print_err "Неизвестный режим: ${INSTALL_MODE}"
        exit 1
        ;;
    esac
}

main "$@"
