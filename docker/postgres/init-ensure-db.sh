#!/bin/sh
# Создаёт БД kotaemon при отсутствии (для старых volumes и гонок запуска)
set -e
until pg_isready -h postgres -U kotaemon; do
  echo "Waiting for postgres..."
  sleep 2
done
psql -h postgres -U kotaemon -d postgres -v ON_ERROR_STOP=1 -tc "SELECT 1 FROM pg_database WHERE datname='kotaemon'" | grep -q 1 || \
  psql -h postgres -U kotaemon -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE kotaemon"
echo "Database kotaemon ready"
