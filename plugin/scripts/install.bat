@echo off
rem mcode-themes 安装脚本（Windows .bat）
rem 需要 Python 3.8+ 和 Node.js 在 PATH 中

echo ==^> 安装 MiniMax Code Themes 插件
set PLUGIN_DIR=%~dp0..

rem 1. 数据目录（%LOCALAPPDATA%\minimax 优先，fallback ~/.minimax）
if defined LOCALAPPDATA (
    set DATA_DIR=%LOCALAPPDATA%\minimax
) else (
    set DATA_DIR=%USERPROFILE%\.minimax
)
set THEME_DIR=%DATA_DIR%\themes
set BIN_DIR=%USERPROFILE%\.local\bin

rem 2. 安装主题文件
if not exist "%THEME_DIR%" mkdir "%THEME_DIR%"
copy /Y "%PLUGIN_DIR%\themes\*.json" "%THEME_DIR%" >nul
echo     主题已复制到 %THEME_DIR%

rem 3. 安装 mcode-theme 工具
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
copy /Y "%PLUGIN_DIR%\mcode-theme" "%BIN_DIR%\mcode-theme" >nul
copy /Y "%PLUGIN_DIR%\mcode_theme_lib.py" "%BIN_DIR%\mcode_theme_lib.py" >nul
echo     工具已复制到 %BIN_DIR%

rem 4. 安装 theme-manager skill
if not exist "%DATA_DIR%\skills" mkdir "%DATA_DIR%\skills"
if not exist "%DATA_DIR%\skills\theme-manager" (
    xcopy /E /I /Y "%PLUGIN_DIR%\plugin\skills\theme-manager" "%DATA_DIR%\skills\theme-manager" >nul
    echo     skill 已安装
) else (
    echo     skill 已存在，跳过
)

echo.
echo ==^> 完成！
echo     mcode-theme list
echo     mcode-theme apply ember
echo     mcode-theme plan violet
pause
