# mcode-theme

MiniMax Code CLI 主题管理插件（Agent Plugins / agent-plugins.org 标准）。

让用户自定义 MiniMax Code CLI（mcode）的界面主题：22 个内置主题（经典社区配色）、
五段渐变 Logo（上浅下深）、一键应用/恢复（备份缺失自动从 npm 官方包还原）、
状态查看、Web 可视化配置器、主题包导出/导入、12 条纪律自动校验、mcode 升级检测。

## 功能

- `mcode-theme list / apply / restore / current / plan` — 主题管理（current 含状态判定）
- `mcode-theme web` — Web 可视化配置器（实时预览 + 真实会话预览 + 主题包导入导出 + 状态卡）
- `mcode-theme install <theme.json|URL>` — 校验（12 条纪律）后安装
- `mcode-theme update` — 检测 mcode 升级并提示重新应用
- `mcode-theme restore` — 恢复官方（备份缺失自动从 npm 全局包还原）
- 22 个内置主题全部通过纪律校验（docs/validation-report.md）

## 安装

```bash
# 方式一：一键脚本（推荐，幂等）
bash install.sh                 # 默认 ~/.local/bin，可 --prefix <目录>
export PATH="$HOME/.local/bin:$PATH"

# 方式二：手动
cp mcode-theme mcode_theme_lib.py web.py logo_styles.py validate-themes.py ~/.local/bin/
cp -r web ~/.local/bin/web/
```

需要 Python 3.8+。`apply` 后重启 mcode 生效。

## 使用

```bash
mcode-theme apply synthwave      # 应用主题
mcode-theme list                 # 列出主题
mcode-theme restore              # 恢复官方
mcode-theme web                  # Web 配置器 → http://localhost:8598
mcode-theme update               # 检测 mcode 升级
```

## Skill

安装本插件后，对 mcode 说“换主题 / 主题 / apply theme”即可触发
`skills/mcode-theme/SKILL.md` 引导完成主题管理。

## 许可

MIT — 见 LICENSE。主题配色转换自 opencode（MIT, https://github.com/anomalyco/opencode）
与 catppuccin/opencode（MIT, https://github.com/catppuccin/opencode）。
