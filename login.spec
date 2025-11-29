# -*- mode: python ; coding: utf-8 -*-


# Incluir automáticamente datos/binarios/hiddenimports de PyMuPDF (fitz/pymupdf)
try:
    from PyInstaller.utils.hooks import collect_all
    _extra_datas = []
    _extra_binaries = []
    _extra_hiddenimports = []
    for _mod in ("fitz", "pymupdf"):
        try:
            _d, _b, _h = collect_all(_mod)
            _extra_datas += _d
            _extra_binaries += _b
            _extra_hiddenimports += _h
        except Exception:
            pass
except Exception:
    _extra_datas = []
    _extra_binaries = []
    _extra_hiddenimports = []


a = Analysis(
    ['login.py'],
    pathex=[],
    binaries=_extra_binaries + [],
    datas=_extra_datas + [],
    hiddenimports=_extra_hiddenimports + [],
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
    a.binaries,
    a.datas,
    [],
    name='login',
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
    icon=['C:\\Users\\hcruz.SIG\\OneDrive - SIG Systems, Inc\\Desktop\\proyecto_app\\login.ico'],
)
