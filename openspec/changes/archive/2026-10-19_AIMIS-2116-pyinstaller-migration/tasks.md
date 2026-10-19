# Tasks — AIMIS-2116 pyinstaller-migration

Перевод сборки core-fa и aivisor на PyInstaller-контур коробки AIMIS. Код сервиса не меняется, вся работа — в deploy-контуре.

## 1. Сборочный контур

- [x] 1.1 `deploy/dockers/Dockerfile.core_fa`: multi-stage builder+runtime, builder — py3.12 + binutils + uv + PyInstaller 6.16.0, выход `/app/cake/run_fa_server.bin`, runtime без python site-packages
- [x] 1.2 `deploy/dockers/Dockerfile.aivisor`: multi-stage builder+runtime, builder — py3.12 + binutils + uv + PyInstaller 6.16.0, выход `/app/cake/run__aivisor_fa_server.bin`, runtime без python site-packages
- [x] 1.3 `deploy/dockers/pyinstaller/specs/core_fa.spec`: spec-файлы обоих образов: collect_submodules по libfa2/agent_stuff/SDK/asynch (aivisor — плюс aivisor), mypyc-глоб coredis 5.4.0, фильтр libgcc_s.so.1
- [x] 1.4 `deploy/dockers/pyinstaller/specs/aivisor.spec`: spec-файлы обоих образов: collect_submodules по libfa2/agent_stuff/SDK/asynch (aivisor — плюс aivisor), mypyc-глоб coredis 5.4.0, фильтр libgcc_s.so.1
- [x] 1.5 `deploy/jenkins/Jenkinsfile.core_fa`: единственный параметр VERSION_BUMP; master бампит версию, ветки — `-PYINSTALLER-SNAPSHOT`; контракты релиза (Release Notes, Quality Gate, AppSec/Sonar) сохранены
- [x] 1.6 `deploy/jenkins/Jenkinsfile.aivisor`: единственный параметр VERSION_BUMP; master бампит версию, ветки — `-PYINSTALLER-SNAPSHOT`; контракты релиза (Release Notes, Quality Gate, AppSec/Sonar) сохранены
- [x] 1.7 Версионирование по git-тегам: `deploy/jenkins/lib/versioning.groovy` (библиотека волны) + `deploy/VERSION` как fallback
- [x] 1.8 Легаси-Nuitka-контур удалён (корневые `Jenkinsfile__*.groovy`, `Dockerfile__aimis2_core_fa`, `Dockerfile__aimis2_aivisor` (Nuitka)); `.gitignore` не глушит deploy-артефакты (spec-файл и версия-либа версионируются)
- [x] 1.9 Стартовый контракт: прежний CMD переведён в ENTRYPOINT (оба образа)

## 2. Зависимости и данные бандла

- [x] 2.1 mypyc-глоб coredis и фильтр libgcc_s.so.1 (GLIBC-конфликт mypyc-расширения в минимальном runtime-базе)
- [x] 2.2 Контракт поставки сверен: appComponent, бинарь, вход src/run__fa_server.py и src/run__aivisor_fa_server.py

## 3. Сервисные адаптации

- [x] 3.1 Окружение юнит-тестов синхронизировано со стеком ранней волны: требования тест-стейджа приведены к актуальным версиям зависимостей

## 4. Сборка и публикация

- [x] 4.1 Первая Jenkins-сборка feature-ветки подняла полный бандл (образ опубликован с тегом `-PYINSTALLER-SNAPSHOT`)
- [x] 4.2 Явные правила спеки проверены на реальной сборке: datas/metadata/vendored присутствуют в `_internal` бандла

## 5. Закрытие изменения

- [x] 5.1 Совокупный результат соответствует критериям приёмки спеки `pyinstaller-build`; артефакты change (`proposal`, `design`, `tasks`, дельта-спека) заполнены, изменение перенесено в `openspec/changes/archive/`
