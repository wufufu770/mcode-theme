# mcode-themes 安装脚本（Windows PowerShell）
# 用法：右键"使用 PowerShell 运行"，或：
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$PluginDir = Split-Path -Parent $PSScriptRoot

# 1. 数据目录（Windows: %LOCALAPPDATA%\minimax，与 mcode 一致）
$DataDir = Join-Path $env:LOCALAPPDATA "minimax"
if (-not (Test-Path $env:LOCALAPPDATA)) {
    $DataDir = Join-Path $env:USERPROFILE ".minimax"
}
$ThemeDir = Join-Path $DataDir "themes"
$BinDir = Join-Path $env:USERPROFILE ".local\bin"

Write-Host "==> 安装 MiniMax Code Themes 插件" -ForegroundColor Cyan
Write-Host "    数据目录: $DataDir"

# 2. 安装主题文件
New-Item -ItemType Directory -Force -Path $ThemeDir | Out-Null
Copy-Item (Join-Path $PluginDir "themes\*.json") $ThemeDir -Force
$themeCount = (Get-ChildItem (Join-Path $PluginDir "themes\*.json")).Count
Write-Host "    主题: $themeCount 个 -> $ThemeDir"

# 3. 安装 mcode-theme 工具
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
Copy-Item (Join-Path $PluginDir "mcode-theme") (Join-Path $BinDir "mcode-theme") -Force
Copy-Item (Join-Path $PluginDir "mcode_theme_lib.py") (Join-Path $BinDir "mcode_theme_lib.py") -Force
Write-Host "    工具: $BinDir\mcode-theme"

# 4. 安装 theme-manager skill（mcode 自动发现 ~/.minimax/skills）
$SkillSrc = Join-Path $PluginDir "plugin\skills\theme-manager"
$SkillTarget = Join-Path $DataDir "skills\theme-manager"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SkillTarget) | Out-Null
if (-not (Test-Path $SkillTarget)) {
    Copy-Item -Recurse $SkillSrc $SkillTarget
    Write-Host "    skill: $SkillTarget"
} else {
    Write-Host "    skill: 已存在，跳过"
}

Write-Host ""
Write-Host "==> 完成！" -ForegroundColor Green
Write-Host "    mcode-theme list              # 查看主题"
Write-Host "    mcode-theme apply ember       # 切换主题"
Write-Host "    mcode-theme plan violet       # 设置 Plan 模式主题"
Write-Host "    重启 mcode 后生效"
