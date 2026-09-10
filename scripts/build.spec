import argparse
import platform
import subprocess
from tomllib import load

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE

# Parsing the "portable" arg
parser = argparse.ArgumentParser()
parser.add_argument("--portable", action="store_true")
options = parser.parse_args()

with open("pyproject.toml", "rb") as file:
    pyproject = load(file)["project"]

system = platform.system()
name = pyproject["name"]
ICON = None
VERSION = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).decode().strip()

if not VERSION:
    raise ValueError("extracted git version was false, thats illegal.")

a = Analysis(
    ["../src/main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["PIL._tkinter_finder", "PIL._imagingtk"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

include = [a.scripts]
if options.portable:
    include += [a.binaries, a.datas]
exe = EXE(
    pyz,
    *include,
    [],
    exclude_binaries=not options.portable,
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = (
    None
    if options.portable
    else COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=name,
    )
)

if platform.system() == "Darwin":
    app = BUNDLE(
        exe if coll is None else coll,
        name=f"{name}.app",
        icon=ICON,
        bundle_identifier="com.thetimebreaker.personalchemicaldatabase",
        version=VERSION,
        info_plist={
            "NSAppleScriptEnabled": False,
            "NSPrincipalClass": "NSApplication",
        },
    )
