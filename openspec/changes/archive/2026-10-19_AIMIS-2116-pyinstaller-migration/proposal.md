## Why

Сборка core-fa и aivisor шла через Nuitka (корневые `Jenkinsfile__*.groovy`, `Dockerfile__aimis2_core_fa`, `Dockerfile__aimis2_aivisor` (Nuitka)): компиляция в C требовала gcc/make в сборочном образе, отдавала медленные сборки и отдельный тракт, отличный от PyInstaller-контура остальной коробки AIMIS (БТ, roles, main-copilot — первые перешедшие сервисы коробки). Волна унификации коробки переводит оставшиеся сервисы на единый шаблон: один многостадийный Dockerfile, PyInstaller 6.16.0, спека в репозитории, версионирование по git-тегам с параметром VERSION_BUMP вместо версий, зашитых в пайплайн.

В репозитории два образа (aimis2_core_fa, aimis2_aivisor) — переезд выполняется для обоих одним change'ом, версии образов остаются независимыми (свои Jenkinsfile, теги и параметры).

## What Changes

- `deploy/dockers/Dockerfile.core_fa` — multi-stage builder+runtime, выход `/app/cake/run_fa_server.bin` (образ `aimis2_core_fa`)
- `deploy/dockers/pyinstaller/specs/core_fa.spec` — spec-файл PyInstaller
- `deploy/jenkins/Jenkinsfile.core_fa` — единый параметр `VERSION_BUMP`; master бампит версию, ветки собирают `-PYINSTALLER-SNAPSHOT`
- `deploy/dockers/Dockerfile.aivisor` — multi-stage builder+runtime, выход `/app/cake/run__aivisor_fa_server.bin` (образ `aimis2_aivisor`)
- `deploy/dockers/pyinstaller/specs/aivisor.spec` — spec-файл PyInstaller
- `deploy/jenkins/Jenkinsfile.aivisor` — единый параметр `VERSION_BUMP`; master бампит версию, ветки собирают `-PYINSTALLER-SNAPSHOT`

- `deploy/VERSION` / versioning.groovy — версия по git-тегам (`deploy/jenkins/lib/versioning.groovy` — отработанная библиотека волны)
- Легаси-Nuitka-контур удалён: корневые `Jenkinsfile__*.groovy`, `Dockerfile__aimis2_core_fa`, `Dockerfile__aimis2_aivisor` (Nuitka); `.gitignore` больше не глушит deploy-артефакты

Что НЕ меняется: контракт поставки — appComponent aimis2_core_fa / aimis2_aivisor, бинарь run_fa_server.bin / run__aivisor_fa_server.bin, вход src/run__fa_server.py и src/run__aivisor_fa_server.py, runtime-состав зависимостей и поведение сервиса.
## Capabilities

### New Capabilities

- `pyinstaller-build`: как собирается core-fa и aivisor — единый PyInstaller-контур, теги master/ветка, самодостаточность бандла, исключение Nuitka-профиля.

### Modified Capabilities

Пусто. Поведение и предметные возможности сервиса не меняются.

## Impact

- Код сервиса не меняется: вся правка — в `deploy/` (docker, jenkins, VERSION) и `.gitignore`. Вход src/run__fa_server.py и src/run__aivisor_fa_server.py и бинарь run_fa_server.bin / run__aivisor_fa_server.bin те же.
- Рантайм-образ: тот же минимальный базовый слой; из образа уходит компиляционный инструментарий (gdb/strace, где были), стартовый контракт — ENTRYPOINT `/app/cake/<bin>.bin`.
- Релизные теги: master собирает версионный релиз без суффикса, доработочные ветки — с суффиксом `-PYINSTALLER-SNAPSHOT`; ключи образов в GitOps-артефактах (reg.txt/argo.txt/патчи) не переименовываются.
- Скрытые риски старта: секции, не видимые статическому анализу, пакуются спекой явно (см. `design.md`); первая сборка ветки — smoke-проверка бандла.
