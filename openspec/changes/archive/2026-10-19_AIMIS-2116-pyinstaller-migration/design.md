## Context

Старый тракт: Nuitka standalone, корневой Dockerfile, версия зашита в пайплайне; корневые `Jenkinsfile__*.groovy`, `Dockerfile__aimis2_core_fa`, `Dockerfile__aimis2_aivisor` (Nuitka). Остальная коробка AIMIS к этому моменту собиралась PyInstaller'ом 6.16.0 по единому шаблону (БТ, roles, main-copilot — первые перешедшие сервисы коробки), что поддерживало два разных сборочных тракта одного стека и мешало волне унификации.

Специфика core-fa и aivisor: вход src/run__fa_server.py и src/run__aivisor_fa_server.py, appComponent aimis2_core_fa / aimis2_aivisor.

## Goals / Non-Goals

Goals:

- один сборочный тракт для всех веток и релизов: те же Dockerfile и спека на master и feature-ветках;
- версионирование git-тегами с параметром VERSION_BUMP (никаких версий в коде Jenkinsfile);
- самодостаточный бандл: скрытые секции и данные пакуются явно, runtime без python site-packages;
- контракт поставки (appComponent, бинарь, вход, ENV) неизменен — GitOps и приёмка стендов не чувствуют смену пакера.

Non-Goals:

- смена рантайм-версии Python и состава зависимостей;
- изменение предметного поведения сервиса;
- чистка dev-инструментов из списков зависимостей, не связанных со сменой пакера (отдельная задача).

## Decisions

### PyInstaller 6.16.0 и спека в репозитории

Единая версия волны; spec-файл живёт в `deploy/dockers/pyinstaller/specs/` и версионируется (`.gitignore` не глушит deploy-артефакты), multi-stage Dockerfile: builder — py3.12 + binutils + uv + PyInstaller, runtime — минимальный базовый слой без python site-packages.

### Версионирование по git-тегам

`deploy/jenkins/lib/versioning.groovy` + `deploy/VERSION` как fallback: master бампит версию (параметр VERSION_BUMP), ветки собирают `-PYINSTALLER-SNAPSHOT`. Контракты релиза (Release Notes, Quality Gate CI_OK, AppSec/Sonar/Unit Tests на master) сохранены.

### Спека и самодостаточность бандла

spec-файлы обоих образов: collect_submodules по libfa2/agent_stuff/SDK/asynch (aivisor — плюс aivisor), mypyc-глоб coredis 5.4.0, фильтр libgcc_s.so.1.

### Независимые версии двух образов

core_fa и aivisor — отдельные appComponent'ы с раздельными тегами jenkins-version/aimis2_core_fa/v* и jenkins-version/aimis2_aivisor/v*, параметрами VERSION_BUMP; стартовые версии берутся из env пайплайнов, deploy/VERSION в репо не используется. Артефакты дистрибутива сохраняют ключи aimisCoreFaImg/aimisAivisorImg.

## Risks / Trade-offs

- Бандл байткода вместо компиляции: содержимое образа проще просматривается. Принято — образы живут внутри контура, поведение эквивалентно.
- Скрытые импорты: риск MissingModule на старте у секций, не видимых статическому анализу. Митигация: collect_submodules по слоям/библиотекам, явные datas для неимпортируемых данных, первая сборка ветки как smoke.
- mypyc-расширение coredis конфликтует с минимальным runtime (GLIBC): в спеке — mypyc-глоб coredis и фильтр libgcc_s.so.1.
- Runtime без python site-packages: если будущий код начнёт вызывать системный python из образа — его нет. Контроль: спека закрывает зависимости в `_internal` бандла.
