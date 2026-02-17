#!/usr/bin/env bash
# Оборачивает вызов uninstall.sh из корня проекта (TUI)
# Запуск: ./scripts/uninstall.sh  или  ./uninstall.sh

cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec ./uninstall.sh "$@"
