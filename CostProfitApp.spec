# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import ast
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct,
)

# Read the canonical version without importing or starting the application.
config_tree = ast.parse((Path(SPECPATH) / 'app' / 'config.py').read_text(encoding='utf-8-sig'))
app_version = next(ast.literal_eval(node.value) for node in config_tree.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'APP_VERSION' for target in node.targets))
def config_literal(name):
    return next(ast.literal_eval(node.value) for node in config_tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
app_author = config_literal('APP_AUTHOR')
app_copyright = config_literal('APP_COPYRIGHT')
version_tuple = tuple(int(part) for part in app_version.split('.')) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple,
                      mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', app_author),
            StringStruct('LegalCopyright', app_copyright),
            StringStruct('FileDescription', 'Invoice'),
            StringStruct('FileVersion', app_version),
            StringStruct('InternalName', 'Invoice'),
            StringStruct('OriginalFilename', 'Invoice.exe'),
            StringStruct('ProductName', 'Invoice'),
            StringStruct('ProductVersion', app_version),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
    ],
)
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
    version=version_info,
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
