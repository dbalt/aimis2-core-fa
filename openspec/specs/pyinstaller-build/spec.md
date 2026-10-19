# pyinstaller-build Specification

## Purpose
Как собирается core-fa и aivisor: единый PyInstaller-контур коробки AIMIS (multi-stage Dockerfile, спека в `deploy/dockers/pyinstaller/specs/`, PyInstaller 6.16.0), версионирование по git-тегам с параметром VERSION_BUMP (master — версионный релиз, ветки — `-PYINSTALLER-SNAPSHOT`), самодостаточный бандл (явные vendored-зависимости и datas) и исключение легаси-Nuitka-профиля. Контракт поставки — appComponent, бинарь, вход — зафиксирован и от смены пакера не зависит.

Возможность заведена унификацией сборочного контура коробки AIMIS; первое исполнение в этом сервисе — AIMIS-2116.

## Requirements
### Requirement: Сборка core-fa и aivisor выполняется PyInstaller-контуром коробки AIMIS

Сборка core-fa и aivisor SHALL выполняться единым PyInstaller-контуром: многостадийные Dockerfile в `deploy/dockers/` (builder: py3.12 + binutils + uv + PyInstaller 6.16.0; runtime: минимальный базовый слой без python site-packages), spec-файлы в `deploy/dockers/pyinstaller/specs/`, версионирование по git-тегам через `deploy/jenkins/lib/versioning.groovy` и параметр VERSION_BUMP. Контракт поставки — appComponent `aimis2_core_fa / aimis2_aivisor`, бинарь `run_fa_server.bin / run__aivisor_fa_server.bin`, вход `src/run__fa_server.py и src/run__aivisor_fa_server.py` — не меняется.

#### Scenario: Релизная сборка master

- **WHEN** Jenkins собирает ветку master
- **THEN** образ получает версионный тег (бамп по параметру VERSION_BUMP), без суффикса
- **AND** релизные контракты пайплайна (Release Notes, Quality Gate CI_OK, AppSec/Sonar/Unit Tests) выполняются

#### Scenario: Сборка доработочной ветки

- **WHEN** Jenkins собирает любую ветку, кроме master
- **THEN** используется тот же Dockerfile и спека, что и для master — второго сборочного тракта нет
- **AND** образ публиковается с суффиксом `-PYINSTALLER-SNAPSHOT`
#### Scenario: Старт контейнера aimis2_core_fa

- **WHEN** контейнер образа `aimis2_core_fa` запускается на стенде
- **THEN** единственный стартовый вход — ENTRYPOINT `/app/cake/run_fa_server.bin`
- **AND** системные python site-packages (`/usr/lib*/.../site-packages`, `/usr/local/lib*/...`) в runtime-слое отсутствуют

#### Scenario: Старт контейнера aimis2_aivisor

- **WHEN** контейнер образа `aimis2_aivisor` запускается на стенде
- **THEN** единственный стартовый вход — ENTRYPOINT `/app/cake/run__aivisor_fa_server.bin`
- **AND** системные python site-packages (`/usr/lib*/.../site-packages`, `/usr/local/lib*/...`) в runtime-слое отсутствуют

#### Scenario: Независимые версии образов в одном репозитории

- **WHEN** собираются образы `aimis2_core_fa` и `aimis2_aivisor` из одного репозитория
- **THEN** каждый образ получает версию из собственного набора git-тегов своим Jenkinsfile
- **AND** параметр VERSION_BUMP применяется к каждому пайплайну независимо; артефакты стадии дистрибутива сохраняют прежние ключи образов

### Requirement: Легаси-Nuitka-профиль сборки исключён

Сборочный контур репозитория SHALL существовать в единственном экземпляре: корневые `Jenkinsfile__*.groovy`, `Dockerfile__aimis2_core_fa`, `Dockerfile__aimis2_aivisor` (Nuitka) удалены, `.gitignore` не исключает deploy-артефакты, пост-патч ELF (там, где применялся) больше не используется — PyInstaller-бандлы в нём не нуждаются.

#### Scenario: Поиск Nuitka-профиля в сборочном контуре

- **WHEN** в репозитории ищется активный Nuitka-профиль (запуск `nuitka` в Dockerfile/Jenkinsfile, elfpatch-стейдж, сборочные nuitka/patchelf в requirements)
- **THEN** активных вхождений нет — упоминания только исторические
- **AND** `deploy/dockers/pyinstaller/specs/` и `deploy/jenkins/lib/versioning.groovy` версионируются (gitignore не глушит)
