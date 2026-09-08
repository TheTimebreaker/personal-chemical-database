# -*- mode: python ; coding: utf-8 -*-
import subprocess
import os
import sys

# uv-managed Python installation
UV_PREFIX = sys.base_prefix
UV_LIB = os.path.join(UV_PREFIX, "lib")

# Make PyInstaller's dependency analysis prefer the libraries
# belonging to the Python installation we're actually building with.
old_ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
os.environ["LD_LIBRARY_PATH"] = (
    UV_LIB
    if not old_ld_library_path
    else UV_LIB + os.pathsep + old_ld_library_path
)

print(f"Using Python base prefix: {UV_PREFIX}")
print(f"Using library path: {UV_LIB}")

tcl_lib = os.path.join(UV_LIB, "libtcl9.0.so")
tk_lib = os.path.join(UV_LIB, "libtcl9tk9.0.so")

a = Analysis(
    ['../src/main.py'],
    pathex=[],
    binaries=[
        #(tcl_lib, "."),
        #(tk_lib, "."),
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

version = subprocess.check_output(
    ["git", "describe", "--tags", "--abbrev=0"]
).decode().strip()

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'personal-chemical-database_{version}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[],
)
