#!/usr/bin/env -S uv run PyInstaller

import argparse
import os
import sys

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

# Parsing the "portable" arg
parser = argparse.ArgumentParser()
parser.add_argument("--portable", action="store_true")
options = parser.parse_args()


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
