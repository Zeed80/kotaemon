#!/bin/bash
# Обновление и пересборка Kotaemon в Docker Compose.
#
# Исходники монтируются (.:/app), поэтому обновление кода — git pull + restart,
# без долгой пересборки (десятки минут).
#
# Использование:
#   ./scripts/docker-update.sh           # git pull + restart (быстро)
#   ./scripts/docker-update.sh --force   # git pull + полная пересборка образа
#   ./scripts/docker-update.sh --force --ssh   # пересборка с SSH (для приватных Git-репо)
#   ./scripts/docker-update.sh --no-pull # только restart (без git pull)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

FORCE_REBUILD=false
NO_PULL=false
USE_SSH=false

while [[ $# -gt 0 ]]; do
    case "$1" in
    --force|-f)
        FORCE_REBUILD=true
        shift
        ;;
    --ssh)
        USE_SSH=true
        shift
        ;;
    --no-pull)
        NO_PULL=true
        shift
        ;;
    --help|-h)
        echo "Использование: $0 [--force|--ssh|--no-pull]"
        echo ""
        echo "  --force, -f   Выполнить полную пересборку образа (при изменении Dockerfile/deps)"
        echo "  --ssh         Передавать SSH-агент в сборку (для приватных Git-репо)"
        echo "  --no-pull     Не выполнять git pull"
        echo ""
        exit 0
        ;;
    *)
        echo "Неизвестный аргумент: $1. Используйте --help"
        exit 1
        ;;
    esac
done

echo "=== Kotaemon Docker: обновление и перезапуск ==="

if [[ "${NO_PULL}" == "false" ]]; then
    echo ""
    echo "Обновление из репозитория..."
    git pull
fi

if [[ "${FORCE_REBUILD}" == "true" ]]; then
    echo ""
    echo "Пересборка образа..."
    if [[ "${USE_SSH}" == "true" ]]; then
        docker compose build --ssh default
    else
        docker compose build
    fi
    echo ""
    echo "Перезапуск контейнеров..."
    docker compose up -d
else
    echo ""
    echo "Перезапуск приложения (исходники монтируются — код уже обновлён)..."
    docker compose restart app
fi

echo ""
echo "Готово. Интерфейс: http://localhost:${KOTAEMON_PORT:-7860}"
echo "Логи: docker compose logs -f app"
