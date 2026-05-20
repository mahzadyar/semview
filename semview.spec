# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SEMView GUI application.
Builds a standalone executable with all dependencies bundled.

Usage: pyinstaller semview.spec
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all tifffile data files and submodules for proper bundling
tifffile_datas = collect_data_files('tifffile')
tifffile_hiddenimports = collect_submodules('tifffile')

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=tifffile_datas,
    hiddenimports=[
        'tkinter',
        'numpy',
        'tifffile',
        'json',
        'os',
        'sys',
        'threading',
    ] + tifffile_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SEMView',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
