#!/usr/bin/env python3
"""Проверка API: маршруты и доступность приложения.

Запуск из корня проекта:
  # После старта Kotaemon (Docker / python app.py / uvicorn app_fastapi:app)
  python scripts/test_api.py http://localhost:7860

  # Только проверка маршрутов (без HTTP-запросов)
  python scripts/test_api.py --routes-only
"""

import argparse
import sys
from pathlib import Path

# Добавить корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests


def check_routes_only():
    """Проверить, что API маршруты зарегистрированы."""
    try:
        from ktem.api.routes import router
    except Exception as e:
        print(f"Ошибка импорта ktem.api: {e}")
        return False
    routes = [r for r in router.routes if hasattr(r, "path")]
    if not routes:
        print("API маршруты не найдены")
        return False
    print("API маршруты:")
    for r in routes:
        path = getattr(r, "path", str(r))
        methods = getattr(r, "methods", set) or "-"
        print(f"  {path} {methods}")
    return True


def check_endpoints(base_url: str) -> bool:
    """Проверить доступность эндпоинтов."""
    base = base_url.rstrip("/")
    ok = True

    # GET /api/v1/jobs/{id} — должен вернуть 404 для несуществующего job
    try:
        r = requests.get(f"{base}/api/v1/jobs/nonexistent", timeout=5)
        if r.status_code == 404:
            print("GET /api/v1/jobs/{job_id}: OK (404 для несуществующего job)")
        elif r.status_code == 401:
            print("GET /api/v1/jobs/{job_id}: OK (401 — требуется API key)")
        else:
            print(f"GET /api/v1/jobs/{{job_id}}: {r.status_code}")
    except requests.RequestException as e:
        print(f"GET /api/v1/jobs/{{job_id}}: ошибка — {e}")
        ok = False

    # POST /api/v1/query — без body должен вернуть 422
    try:
        r = requests.post(f"{base}/api/v1/query", json={}, timeout=5)
        if r.status_code in (422, 400):
            print("POST /api/v1/query: OK (422/400 без question)")
        elif r.status_code == 401:
            print("POST /api/v1/query: OK (401 — требуется API key)")
        else:
            print(f"POST /api/v1/query: {r.status_code}")
    except requests.RequestException as e:
        print(f"POST /api/v1/query: ошибка — {e}")
        ok = False

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "base_url",
        nargs="?",
        default=None,
        help="Base URL (e.g. http://localhost:7860)",
    )
    parser.add_argument(
        "--routes-only",
        action="store_true",
        help="Только проверить маршруты (без HTTP)",
    )
    args = parser.parse_args()

    if args.routes_only:
        if check_routes_only():
            print("\nПроверка маршрутов: OK")
            sys.exit(0)
        sys.exit(1)

    if not args.base_url:
        print("Укажите base_url или --routes-only")
        sys.exit(1)

    if check_routes_only() and check_endpoints(args.base_url):
        print("\nПроверка API: OK")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
