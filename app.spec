# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('index.html', '.'),   # 把 HTML 文件打包进去
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'click',
        'jinja2',
        'itsdangerous',
        'webview',
        'webview.platforms.winforms',
        'clr',
        'sqlite3',
        'engineio',
        'server',
        'pdfplumber',
        'pdfminer',
        'pdfminer.high_level',
        'pdfminer.layout',
        'pdfminer.pdfpage',
        'pdfminer.pdfinterp',
        'pdfminer.converter',
        'pdfminer.pdfdocument',
        'pdfminer.pdfparser',
        'Cryptodome',
        'Cryptodome.Cipher',
        'Cryptodome.Cipher.ARC4',
        'Cryptodome.Cipher.AES',
        'Cryptodome.Cipher.DES',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CardTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # 不显示黑色命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CardTracker',
)
