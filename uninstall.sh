#!/usr/bin/env bash
# Kotaemon — полное удаление (TUI)
# Запуск из корня проекта: ./uninstall.sh

set -euo pipefail
[[ -n "${DEBUG:-}" ]] && set -x

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

# Volumes, контейнеры, образы
VOLUMES=(kotaemon_ktem_app_data kotaemon_qdrant_data kotaemon_postgres_data kotaemon_ollama_models)
CONTAINERS=(kotaemon kotaemon-db-init kotaemon-postgres kotaemon-qdrant kotaemon-searxng kotaemon-ollama)
IMAGES=(kotaemon:latest)
IMAGES_DEPS=(searxng/searxng:latest pgvector/pgvector:pg16 qdrant/qdrant:latest)

clear_screen() { printf '\033[2J\033[H'; }

print_header() {
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║           Kotaemon — полное удаление                     ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
}

show_status() {
  local migrate_opt="нет"; [[ "${opt_migrate}" == "1" ]] && migrate_opt="да"
  local docker_opt="нет";  [[ "${opt_docker}" == "1" ]]  && docker_opt="да"
  local deps_opt="нет";    [[ "${opt_deps}" == "1" ]]   && deps_opt="да"
  local local_opt="нет";   [[ "${opt_local}" == "1" ]]  && local_opt="да"
  local env_opt="сохранить"; [[ "${opt_env}" == "1" ]]  && env_opt="удалить"

  echo "  [1] Резервная копия (миграция)              : ${migrate_opt}"
  echo "  [2] Docker (контейнеры, volumes)            : ${docker_opt}"
  echo "  [3] Образы зависимостей (searxng, pgvector, qdrant) : ${deps_opt}"
  echo "  [4] Локальные папки (.venv, install_dir, ktem_app_data) : ${local_opt}"
  echo "  [5] .env                                   : ${env_opt}"
  echo ""
  echo "  [0] Выполнить удаление"
  echo "  [q] Выход"
  echo ""
}

toggle() {
  local var="$1"
  if [[ "${!var}" == "1" ]]; then
    printf -v "$var" "0"
  else
    printf -v "$var" "1"
  fi
}

do_migrate() {
  local stamp
  stamp=$(date +%Y%m%d_%H%M%S)
  local backup_dir="${REPO_ROOT}/backup_kotaemon_${stamp}"
  mkdir -p "${backup_dir}"
  echo ""
  echo "  Миграция в ${backup_dir}"

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q kotaemon-postgres; then
    docker exec kotaemon-postgres pg_dump -U kotaemon kotaemon > "${backup_dir}/postgres_dump.sql" 2>/dev/null && echo "  [OK] PostgreSQL dump"
  fi

  for vol in "${VOLUMES[@]}"; do
    if docker volume ls -q 2>/dev/null | grep -q "^${vol}$"; then
      local dest="${backup_dir}/volumes/${vol}"
      mkdir -p "${dest}"
      docker run --rm -v "${vol}:/src:ro" -v "${dest}:/dst" alpine cp -a /src/. /dst/ 2>/dev/null && echo "  [OK] Volume ${vol}"
    fi
  done

  [[ -d "${REPO_ROOT}/ktem_app_data" ]] && cp -a "${REPO_ROOT}/ktem_app_data" "${backup_dir}/" 2>/dev/null && echo "  [OK] ktem_app_data"
  [[ -f "${REPO_ROOT}/.env" ]] && cp -a "${REPO_ROOT}/.env" "${backup_dir}/" && echo "  [OK] .env"
  echo "  Резервная копия: ${backup_dir}"
}

do_docker_remove() {
  if ! command -v docker &>/dev/null; then
    echo "  [!] Docker не найден"
    return
  fi
  echo ""
  echo "  Удаление Docker..."

  docker compose down -v 2>/dev/null || docker-compose down -v 2>/dev/null || true
  for c in "${CONTAINERS[@]}"; do docker rm -f "${c}" 2>/dev/null || true; done
  for img in "${IMAGES[@]}"; do docker rmi -f "${img}" 2>/dev/null || true; done
  if [[ "${opt_deps}" == "1" ]]; then
    for img in "${IMAGES_DEPS[@]}"; do docker rmi -f "${img}" 2>/dev/null || true; done
  fi
  for vol in "${VOLUMES[@]}"; do docker volume rm -f "${vol}" 2>/dev/null || true; done
  echo "  [OK] Docker удалён"
}

do_local_remove() {
  echo ""
  echo "  Удаление локальных папок..."
  [[ -d "${REPO_ROOT}/.venv" ]] && rm -rf "${REPO_ROOT}/.venv" && echo "  [OK] .venv"
  [[ -d "${REPO_ROOT}/install_dir" ]] && rm -rf "${REPO_ROOT}/install_dir" && echo "  [OK] install_dir"
  [[ -d "${REPO_ROOT}/ktem_app_data" ]] && rm -rf "${REPO_ROOT}/ktem_app_data" && echo "  [OK] ktem_app_data"
  [[ -d "${REPO_ROOT}/flow_tmp" ]] && rm -rf "${REPO_ROOT}/flow_tmp" && echo "  [OK] flow_tmp"
  [[ -d "${REPO_ROOT}/qdrant_data" ]] && rm -rf "${REPO_ROOT}/qdrant_data" && echo "  [OK] qdrant_data"
  if [[ "${opt_env}" == "1" ]] && [[ -f "${REPO_ROOT}/.env" ]]; then
    rm -f "${REPO_ROOT}/.env" && echo "  [OK] .env"
  fi
}

run_uninstall() {
  [[ "${opt_migrate}" == "1" ]] && do_migrate
  [[ "${opt_docker}" == "1" ]] && do_docker_remove
  [[ "${opt_local}" == "1" ]] && do_local_remove
  echo ""
  echo "  Готово."
  echo ""
}

# --- TUI ---
opt_migrate=0
opt_docker=1
opt_deps=0
opt_local=1
opt_env=0

while true; do
  clear_screen
  print_header
  show_status
  read -r -p "Выбор [0-5, q]: " choice

  case "${choice}" in
  1) toggle opt_migrate ;;
  2) toggle opt_docker ;;
  3) toggle opt_deps ;;
  4) toggle opt_local ;;
  5) toggle opt_env ;;
  0)
    if [[ "${opt_docker}" == "0" ]] && [[ "${opt_local}" == "0" ]]; then
      echo "Выберите хотя бы Docker или локальные папки."
      read -r -p "Нажмите Enter..."
      continue
    fi
    echo ""
    read -r -p "Подтвердить удаление? [y/N] " ans
    if [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]; then
      run_uninstall
      exit 0
    fi
    ;;
  q|Q) exit 0 ;;
  *) ;;
  esac
done
