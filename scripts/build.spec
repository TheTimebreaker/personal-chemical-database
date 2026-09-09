import argparse
import os
import sys

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

# Parsing the "portable" arg
parser = argparse.ArgumentParser()
parser.add_argument("--portable", action="store_true")
options = parser.parse_args()

# Find paths to tcl/tk version of the UV venv, because not declaring this explicitly APPARENTLY makes pyinstaller add wrong/incompatible versions
UV_PREFIX = sys.base_prefix
UV_LIB = os.path.join(UV_PREFIX, "lib")
old_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
os.environ["LD_LIBRARY_PATH"] = UV_LIB if not old_ld_library_path else UV_LIB + os.pathsep + old_ld_library_path
print(f"Using Python base prefix: {UV_PREFIX}")
print(f"Using library path: {UV_LIB}")
tcl_lib = os.path.join(UV_LIB, "libtcl9.0.so")
tk_lib = os.path.join(UV_LIB, "libtcl9tk9.0.so")

a = Analysis(
    ["../src/main.py"],
    pathex=[],
    binaries=[
        (tcl_lib, "."),
        (tk_lib, "."),
    ],
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
    name="personal-chemical-database",
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
        name="personal-chemical-database",
    )
)
