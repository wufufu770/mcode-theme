#!/usr/bin/env bash
# mcode-themes 插件安装脚本
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${MINIMAX_THEME_DIR:-$HOME/.minimax/themes}"
BIN_DIR="${MINIMAX_THEME_BIN:-$HOME/.local/bin}"

echo "==> 安装 MiniMax Code Themes 插件"

# 1. 安装主题文件
mkdir -p "$DEST_DIR"
cp "$PLUGIN_DIR"/themes/*.json "$DEST_DIR"/
echo "    主题: $(ls "$PLUGIN_DIR"/themes/*.json | wc -l) 个 -> $DEST_DIR"

# 2. 安装 mcode-theme 工具
mkdir -p "$BIN_DIR"
cp "$PLUGIN_DIR"/scripts/mcode-theme "$BIN_DIR"/mcode-theme
chmod +x "$BIN_DIR"/mcode-theme
echo "    工具: $BIN_DIR/mcode-theme"

# 3. 安装 theme-manager skill（mcode 自动发现 ~/.claude/skills）
SKILL_SRC="$PLUGIN_DIR/skills/theme-manager"
for target in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  mkdir -p "$target"
  if [ ! -e "$target/theme-manager" ]; then
    cp -r "$SKILL_SRC" "$target/theme-manager"
    echo "    skill: $target/theme-manager"
  else
    echo "    skill: 已存在，跳过 $target/theme-manager"
  fi
done

echo ""
echo "==> 完成！"
echo "    mcode-theme list              # 查看主题"
echo "    mcode-theme apply ember       # 切换主题"
echo "    mcode-theme plan violet       # 设置 Plan 模式主题"
echo "    重启 mcode 后生效"
