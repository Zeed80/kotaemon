@ECHO off
REM Kotaemon — полное удаление (Windows)
REM Использование: scripts\uninstall.bat [--migrate] [--force] [--docker-only | --local-only] [--keep-env]
REM --migrate   Сохранить резервную копию в backup_kotaemon_YYYYMMDD_HHMMSS\
REM --force     Без подтверждения

SETLOCAL
CD /D "%~dp0\.."
SET "REPO_ROOT=%CD%"
SET "BACKUP_DIR="
SET "MIGRATE=0"
SET "FORCE=0"
SET "DOCKER_ONLY=0"
SET "LOCAL_ONLY=0"
SET "KEEP_ENV=0"

:parse_args
IF "%~1"=="" GOTO :run
IF /I "%~1"=="--migrate" SET MIGRATE=1
IF /I "%~1"=="-m" SET MIGRATE=1
IF /I "%~1"=="--force" SET FORCE=1
IF /I "%~1"=="-f" SET FORCE=1
IF /I "%~1"=="--docker-only" SET DOCKER_ONLY=1
IF /I "%~1"=="--local-only" SET LOCAL_ONLY=1
IF /I "%~1"=="--keep-env" SET KEEP_ENV=1
IF /I "%~1"=="--help" GOTO :help
SHIFT
GOTO :parse_args

:help
ECHO Kotaemon uninstall: scripts\uninstall.bat [--migrate] [--force] [--docker-only ^| --local-only] [--keep-env]
EXIT /B 0

:run
ECHO.
ECHO ******************************************************
ECHO Kotaemon — полное удаление
ECHO ******************************************************
ECHO.

REM Миграция
IF %MIGRATE%==1 (
  SET "stamp=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
  SET "stamp=%stamp: =0%"
  SET "BACKUP_DIR=%REPO_ROOT%\backup_kotaemon_%stamp%"
  MKDIR "%BACKUP_DIR%" 2>nul
  ECHO Резервная копия в %BACKUP_DIR%

  docker ps --format "{{.Names}}" 2>nul | findstr kotaemon-postgres >nul && (
    docker exec kotaemon-postgres pg_dump -U kotaemon kotaemon > "%BACKUP_DIR%\postgres_dump.sql" 2>nul
    ECHO [OK] PostgreSQL dump
  )

  IF EXIST "%REPO_ROOT%\.env" COPY "%REPO_ROOT%\.env" "%BACKUP_DIR%\" >nul && ECHO [OK] .env
  IF EXIST "%REPO_ROOT%\ktem_app_data" XCOPY /E /I /Q "%REPO_ROOT%\ktem_app_data" "%BACKUP_DIR%\ktem_app_data" >nul && ECHO [OK] ktem_app_data
  ECHO Резервная копия: %BACKUP_DIR%
  ECHO.
)

REM Подтверждение
IF %FORCE%==0 (
  SET /P "ans=Удалить Kotaemon (контейнеры, образы, volumes, папки)? [y/N]: "
  IF /I NOT "%ans%"=="y" IF /I NOT "%ans%"=="yes" EXIT /B 0
)

REM Docker и локальные папки
IF %DOCKER_ONLY%==1 (
  CALL :docker
  GOTO :done
)
IF %LOCAL_ONLY%==1 (
  CALL :local
  GOTO :done
)
CALL :docker
CALL :local
GOTO :done

:docker
IF EXIST "%REPO_ROOT%\docker-compose.yml" (
  docker compose down -v 2>nul || docker-compose down -v 2>nul
)
FOR %%c IN (kotaemon kotaemon-db-init kotaemon-postgres kotaemon-qdrant kotaemon-searxng kotaemon-ollama) DO docker rm -f %%c 2>nul
docker rmi -f kotaemon:latest 2>nul
FOR %%v IN (kotaemon_ktem_app_data kotaemon_qdrant_data kotaemon_postgres_data kotaemon_ollama_models) DO docker volume rm -f %%v 2>nul
ECHO [OK] Docker удалён
EXIT /B 0

:local
IF EXIST "%REPO_ROOT%\.venv" RMDIR /S /Q "%REPO_ROOT%\.venv" && ECHO [OK] .venv
IF EXIST "%REPO_ROOT%\install_dir" RMDIR /S /Q "%REPO_ROOT%\install_dir" && ECHO [OK] install_dir
IF EXIST "%REPO_ROOT%\ktem_app_data" RMDIR /S /Q "%REPO_ROOT%\ktem_app_data" && ECHO [OK] ktem_app_data
IF EXIST "%REPO_ROOT%\flow_tmp" RMDIR /S /Q "%REPO_ROOT%\flow_tmp" && ECHO [OK] flow_tmp
IF EXIST "%REPO_ROOT%\qdrant_data" RMDIR /S /Q "%REPO_ROOT%\qdrant_data" && ECHO [OK] qdrant_data
IF %KEEP_ENV%==0 IF EXIST "%REPO_ROOT%\.env" DEL "%REPO_ROOT%\.env" && ECHO [OK] .env
EXIT /B 0

:done
ECHO.
ECHO ******************************************************
ECHO Kotaemon удалён
ECHO ******************************************************
EXIT /B 0
