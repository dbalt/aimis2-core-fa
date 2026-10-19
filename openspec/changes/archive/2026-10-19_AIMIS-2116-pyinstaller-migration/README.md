# AIMIS-2116 — pyinstaller-migration

Перевод сборки core-fa и aivisor с Nuitka на единый PyInstaller-контур коробки AIMIS (AIMIS-2116): PyInstaller 6.16.0 в многостадийном Dockerfile, спека в `deploy/dockers/pyinstaller/specs/`, версионирование через git-теги и параметр `VERSION_BUMP`. Легаси-Nuitka-контур (корневые `Jenkinsfile__*.groovy`, `Dockerfile__aimis2_core_fa`, `Dockerfile__aimis2_aivisor` (Nuitka)) удалён; контракт поставки (имя образа, бинарь, вход) не меняется.
