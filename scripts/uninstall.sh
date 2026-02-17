#!/usr/bin/env bash
# Kotaemon — полное удаление проекта, образов, контейнеров и папок
# Использование: ./scripts/uninstall.sh [--migrate] [--force] [--docker-only | --local-only] [--keep-env]
#
# --migrate, -m   Сохранить резервную копию данных (PostgreSQL dump, volumes, .env) в backup_kotaemon_YYYYMMDD_HHMMSS/
# --force, -f     Без подтверждения
# --docker-only   Только Docker (контейнеры, образы, volumes)
# --local-only    Только локальные артефакты (.venv, install_dir, ktem_app_data)
# --keep-env      Не удалять .env

set -euo pipefail
[[ -n "${DEBUG:-}" ]] && set -x

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${__dir}/.." && pwd)"

# Volumes Kotaemon (имена из docker-compose.yml)
VOLUMES=(
  kotaemon_ktem_app_data
  kotaemon_qdrant_data
  kotaemon_postgres_data
  kotaemon_ollama_models
)
CONTAINERS=(
  kotaemon
  kotaemon-db-init
  kotaemon-postgres
  kotaemon-qdrant
  kotaemon-searxng
  kotaemon-ollama
)
IMAGES=(
  kotaemon:latest
)

MIGRATE=false
FORCE=false
DOCKER_ONLY=false
LOCAL_ONLY=false
KEEP_ENV=false

# --- Разбор аргументов ---
while [[ $# -gt 0 ]]; do
  case "$1" in
  --migrate|-m)
    MIGRATE=true
    shift
    ;;
  --force|-f)
    FORCE=true
    shift
    ;;
  --docker-only)
    DOCKER_ONLY=true
    shift
    ;;
  --local-only)
    LOCAL_ONLY=true
    shift
    ;;
  --keep-env)
    KEEP_ENV=true
    shift
    ;;
  --help|-h)
    head -18 "$0" | tail -14
    exit 0
    ;;
  *)
    echo "Неизвестный аргумент: $1"
    exit 1
    ;;
  esac
done

print_step() {
  echo ""
  echo "******************************************************"
  echo "$1"
  echo "******************************************************"
  echo ""
}

print_ok() { echo "[OK] $1"; }
print_warn() { echo "[!] $1" >&2; }
print_err() { echo "[ERROR] $1" >&2; }

confirm() {
  if [[ "${FORCE}" == "true" ]]; then
    return 0
  fi
  local msg="${1:-Продолжить?}"
  read -r -p "${msg} [y/N] " ans
  [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

# --- Миграция (резервная копия) ---
do_migrate() {
  local stamp
  stamp=$(date +%Y%m%d_%H%M%S)
  local backup_dir="${REPO_ROOT}/backup_kotaemon_${stamp}"
  mkdir -p "${backup_dir}"
  print_step "Миграция данных в ${backup_dir}"

  # PostgreSQL dump
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q kotaemon-postgres; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q kotaemon-postgres; then
      print_ok "Дамп PostgreSQL..."
      docker exec kotaemon-postgres pg_dump -U kotaemon kotaemon > "${backup_dir}/postgres_dump.sql" 2>/dev/null || true
    else
      print_warn "Контейнер postgres остановлен, дамп пропущен"
    fi
  fi

  # Volumes → backup (копирование содержимого)
  for vol in "${VOLUMES[@]}"; do
    if docker volume ls -q 2>/dev/null | grep -q "^${vol}$"; then
      local dest="${backup_dir}/volumes/${vol}"
      mkdir -p "${dest}"
      if docker run --rm -v "${vol}:/src:ro" -v "${dest}:/dst" alpine cp -a /src/. /dst/ 2>/dev/null; then
        print_ok "Скопирован volume: ${vol}"
      else
        print_warn "Не удалось скопировать volume: ${vol}"
      fi
    fi
  done

  # Локальная папка ktem_app_data (если есть и не в volume)
  if [[ -d "${REPO_ROOT}/ktem_app_data" ]]; then
    cp -a "${REPO_ROOT}/ktem_app_data" "${backup_dir}/" 2>/dev/null && print_ok "Скопирован ktem_app_data"
  fi

  # .env
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    cp -a "${REPO_ROOT}/.env" "${backup_dir}/" && print_ok "Скопирован .env"
  fi

  echo ""
  echo "Резервная копия сохранена в: ${backup_dir}"
  echo "Восстановление: см. docs/DATA_AND_RESET.md"
}

# --- Остановка и удаление Docker ---
do_docker_remove() {
  if ! command -v docker &>/dev/null; then
    print_warn "Docker не найден, пропуск"
    return
  fi

  print_step "Остановка и удаление Docker"

  cd "${REPO_ROOT}"
  docker compose down -v 2>/dev/null || docker-compose down -v 2>/dev/null || true

  for c in "${CONTAINERS[@]}"; do
    docker rm -f "${c}" 2>/dev/null || true
  done

  for img in "${IMAGES[@]}"; do
    docker rmi -f "${img}" 2>/dev/null || true
  done

  for vol in "${VOLUMES[@]}"; do
    docker volume rm -f "${vol}" 2>/dev/null || true
  done

  print_ok "Docker артефакты удалены"
}

# --- Удаление локальных папок ---
do_local_remove() {
  print_step "Удаление локальных артефактов"

  local removed=()
  [[ -d "${REPO_ROOT}/.venv" ]] && rm -rf "${REPO_ROOT}/.venv" && removed+=(".venv")
  [[ -d "${REPO_ROOT}/install_dir" ]] && rm -rf "${REPO_ROOT}/install_dir" && removed+=("install_dir")
  [[ -d "${REPO_ROOT}/ktem_app_data" ]] && rm -rf "${REPO_ROOT}/ktem_app_data" && removed+=("ktem_app_data")
  [[ -d "${REPO_ROOT}/flow_tmp" ]] && rm -rf "${REPO_ROOT}/flow_tmp" && removed+=("flow_tmp")
  [[ -d "${REPO_ROOT}/qdrant_data" ]] && rm -rf "${REPO_ROOT}/qdrant_data" && removed+=("qdrant_data")

  if [[ ${#removed[@]} -gt 0 ]]; then
    print_ok "Удалены: ${removed[*]}"
  fi

  if [[ "${KEEP_ENV}" != "true" ]] && [[ -f "${REPO_ROOT}/.env" ]]; then
    rm -f "${REPO_ROOT}/.env" && print_ok "Удалён .env"
  elif [[ "${KEEP_ENV}" == "true" ]] && [[ -f "${REPO_ROOT}/.env" ]]; then
    print_ok "Сохранён .env"
  fi
}

# --- Main ---
main() {
  print_step "Kotaemon — полное удаление"

  if [[ "${MIGRATE}" == "true" ]]; then
    do_migrate
  fi

  if [[ "${DOCKER_ONLY}" == "true" ]]; then
    confirm "Удалить контейнеры, образы и volumes Kotaemon?" || exit 0
    do_docker_remove
    print_step "Готово (только Docker)"
    exit 0
  fi

  if [[ "${LOCAL_ONLY}" == "true" ]]; then
    confirm "Удалить .venv, install_dir, ktem_app_data?" || exit 0
    do_local_remove
    print_step "Готово (только локальные артефакты)"
    exit 0
  fi

  # Полное удаление
  confirm "Удалить всё: Docker (контейнеры, образы, volumes) и локальные папки (.venv, install_dir, ktem_app_data)? Это необратимо без --migrate." || exit 0

  do_docker_remove
  do_local_remove

  print_step "Kotaemon полностью удалён"
}

main "$@"
