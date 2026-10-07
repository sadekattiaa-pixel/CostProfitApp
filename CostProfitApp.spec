# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('app/db/schema.sql', 'app/db')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('arabic_reshaper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('bidi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Invoice',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Invoice',
)

# Keep Windows' own UCRT/ICU ahead of unrelated private toolchain copies.
internal_dir = Path(DISTPATH) / 'Invoice' / '_internal'
if internal_dir.is_dir():
    for runtime_file in internal_dir.iterdir():
        name = runtime_file.name.lower()
        if runtime_file.is_file() and (
            name in {'ucrtbase.dll', 'icuuc.dll'}
            or name.startswith('api-ms-win-')
            or (name.startswith('icudt') and name.endswith('.dll'))
        ):
            runtime_file.unlink()
