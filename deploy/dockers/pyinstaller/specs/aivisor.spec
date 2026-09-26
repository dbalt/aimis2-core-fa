from pathlib import Path
import importlib.util

from PyInstaller.utils.hooks import collect_submodules


source_root = Path(SPECPATH).parents[3] / "src"
hiddenimports = []
for package in (
    "aivisor",
    "libfa2",
    "agent_stuff",
    "sdk",
    "platformdirs",
):
    hiddenimports += collect_submodules(package)
# coredis распространяет скомпилированные mypyc-библиотеки: PyInstaller их не
# обнаруживает статическим анализом, подключаем глобом из site-packages.
site_packages = Path(importlib.util.find_spec("coredis").origin).parent.parent
hiddenimports += sorted(library.name.split(".")[0] for library in site_packages.glob("*__mypyc.*.so"))

analysis = Analysis(
    [str(source_root / "run__aivisor_fa_server.py")],
    pathex=[str(source_root)], hiddenimports=hiddenimports,
    binaries=[], datas=[], noarchive=False,
)
# libgcc_s.so.1 из builder-окружения конфликтует с системной GLIBC в runtime-базе.
analysis.binaries = [
    entry for entry in analysis.binaries if Path(entry[0]).name != "libgcc_s.so.1"
]
pyz = PYZ(analysis.pure)
executable = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name="run__aivisor_fa_server.bin", console=True)
bundle = COLLECT(executable, analysis.binaries, analysis.datas, strip=False, upx=False, name="run__aivisor_fa_server.bin")
