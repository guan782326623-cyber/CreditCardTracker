@echo off
chcp 65001 >nul
setlocal

:: 切换到 build.bat 所在目录
cd /d "%~dp0"

echo ============================================================
echo   Amex Tracker — 一键打包脚本
echo ============================================================
echo.

:: ── 第一步：安装 Python 依赖 ──────────────────────────────────
echo [1/3] 安装 Python 依赖...

pip install flask flask-cors pywebview pdfplumber pycryptodome
if %ERRORLEVEL% NEQ 0 (
    echo [错误] flask/pywebview 安装失败。
    pause & exit /b 1
)

:: 清理损坏的 PyInstaller 旧文件（Access Denied 问题的根源）
echo 清理旧版 PyInstaller 残留文件...
del /f /q "C:\Python312\Scripts\pyi-archive_viewer.exe"     2>nul
del /f /q "C:\Python312\Scripts\pyi-bindepend.exe"          2>nul
del /f /q "C:\Python312\Scripts\pyi-grab_version.exe"       2>nul
del /f /q "C:\Python312\Scripts\pyi-makespec.exe"           2>nul
del /f /q "C:\Python312\Scripts\pyinstaller.exe"            2>nul

:: 安装 PyInstaller 到用户目录（绕过系统目录权限问题）
pip install --user --force-reinstall pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo [错误] PyInstaller 安装失败，请查看上方错误信息。
    pause & exit /b 1
)
echo.

:: ── 第二步：PyInstaller 打包 ──────────────────────────────────
echo [2/3] 用 PyInstaller 打包（可能需要几分钟）...
if exist dist\CardTracker rmdir /s /q dist\CardTracker

:: 把临时构建目录放到 %TEMP%，避免 OneDrive 锁文件
set BUILDTMP=%TEMP%\AmexTrackerBuild
if exist "%BUILDTMP%" rmdir /s /q "%BUILDTMP%"

:: 用 python -m PyInstaller 代替直接调用（更可靠）
python -m PyInstaller app.spec --clean --noconfirm --workpath "%BUILDTMP%" --distpath dist
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] PyInstaller 打包失败，请查看上方错误信息。
    pause & exit /b 1
)
echo.

:: ── 第三步：Inno Setup 生成安装程序 ──────────────────────────
echo [3/3] 用 Inno Setup 生成安装包...

set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo.
    echo [提示] 未检测到 Inno Setup 6。
    echo        请从以下地址下载并安装（免费）：
    echo        https://jrsoftware.org/isdl.php
    echo.
    echo        安装后再次双击 build.bat 即可生成安装包。
    echo.
    echo  现在可以直接测试运行：
    echo  dist\CardTracker\CardTracker.exe
    echo.
) else (
    %ISCC% installer.iss
    if %ERRORLEVEL% NEQ 0 (
        echo [错误] Inno Setup 编译失败。
        pause & exit /b 1
    )
    echo.
    echo ============================================================
    echo   完成！安装包已生成：CardTrackerSetup.exe
    echo ============================================================
)

pause
