---
name: theme-manager
description: "管理 MiniMax Code CLI 的主题。列出已安装主题、切换主题、设置/清除 Plan 模式主题、恢复官方主题、随机主题、创建新主题。Triggers: 主题, theme, 换主题, 切换主题, 主题颜色, plan 主题, 配色, 皮肤, skin, 暗色, 亮色."
license: MIT
metadata:
  version: "1.0"
  category: customization
  sources:
    - https://github.com/wufufu770/minimax-code-themes
---

# Theme Manager

管理 MiniMax Code CLI（mcode）的主题。本技能通过 `mcode-theme` 命令行工具操作。

## 工具位置

`mcode-theme` 已安装到 PATH（通常为 `~/.local/bin/mcode-theme`）。若未找到，提示用户运行安装：
```bash
cp mcode-theme ~/.local/bin/mcode-theme && chmod +x ~/.local/bin/mcode-theme
```

## 可用命令

| 命令 | 用途 |
|------|------|
| `mcode-theme list` | 列出所有已安装主题 + 当前主题 + Plan 主题 |
| `mcode-theme current` | 查看当前主题详情 |
| `mcode-theme apply <name>` | 切换主题（21 个内置：ember/emerald/violet/minimax-official/minimax-light/deepseek/dracula/nord/monokai/tokyo-night/synthwave/...） |
| `mcode-theme plan <name>` | 设置 Plan 模式主题（Shift+Tab 进入 Plan 模式时自动切换） |
| `mcode-theme unplan` | 清除 Plan 模式主题 |
| `mcode-theme random` | 随机切换主题 |
| `mcode-theme restore` | 恢复官方默认主题 |
| `mcode-theme create <name>` | 生成新主题模板 |

## 主题清单（21 个）

- **MiniMax 官方**: `minimax-official`（品牌蓝 #68C0FF）, `minimax-light`（亮色）
- **中性风格**: `ember`（暖橙）, `emerald`（翡翠绿）, `violet`（紫罗兰）
- **AI 品牌**: `deepseek`（蓝紫）, `github-dark`（蓝）, `one-dark`, `dracula`, `nord`, `monokai`, `monokai-pro`, `tokyo-night`, `gruvbox-dark`, `synthwave`, `catppuccin-mocha`, `rose-pine`, `material-palenight`, `everforest-dark`, `solarized-dark`, `cyberpunk`

## 工作流程

### 用户要求换主题
1. 先运行 `mcode-theme list` 查看可用主题
2. 若用户指定主题名，直接 `mcode-theme apply <name>`
3. 若用户未指定，推荐 1-3 个合适主题（考虑用户场景：开发/办公/暗色偏好）
4. 告知用户**重新打开 mcode** 生效

### 用户要求 Plan 模式不同主题
```bash
mcode-theme apply <正常主题>    # 正常模式
mcode-theme plan <plan主题>     # Plan 模式（Shift+Tab 切换）
```

### 用户想自定义主题
1. `mcode-theme create <name>` 生成模板
2. 编辑 `~/.minimax/themes/<name>.json` 中的 colors（15 个键：brand/accent/text/muted/dim/border/line/success/warning/error/signal/orbit/userMessageBg/wordmarkHighlight/wordmarkShadow）
3. `mcode-theme install ~/.minimax/themes/<name>.json` 安装

## 注意事项

- 切换主题后必须**重启 mcode**（或 `/quit` 再启动）才生效
- `restore` 会清除所有自定义配置（含 Plan 主题）
- 升级 mcode 后主题被覆盖，需重新 `mcode-theme apply`
- 工具自动做 JS 语法校验，若 patch 失败自动回滚官方版
