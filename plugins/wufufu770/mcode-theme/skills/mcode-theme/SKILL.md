---
name: mcode-theme
description: >-
  Switch or customize the MiniMax Code CLI (mcode) color theme. Use when the user
  asks to "换主题" / "切换主题" / "改配色" / "换个皮肤" / "apply theme" / "主题可视化",
  or wants to list installed themes, restore the default, or open the Web palette editor.
descriptions:
  zh-Hans: "切换或定制 MiniMax Code CLI (mcode) 配色主题。当用户提到「换主题/切换主题/改配色/换个皮肤/主题可视化」时使用。"
displayNames:
  zh-Hans: "mcode 主题"
metadata:
  version: "0.3.0"
  category: productivity
---

# mcode 主题

管理 mcode 的配色主题。主题写入 `~/.minimax/tui/themes/`，mcode 监听该目录并热重载，
所以切换立即生效，不需要重启 mcode。

## 与官方 /theme 的分工

- `/theme` —— mcode 内置面板（↑↓ 选主题，←/→ 切明暗）。用户只是「换个主题」时优先提示用
  这个：它是本地动作，不消耗模型推理。
- `/mcode-theme`（本 Skill）—— 需要组合操作时用：列全部主题、改单个色键、开 Web 调色盘、
  导出/导入主题包。

## 命令

`mcode-theme` 需在 PATH 中（安装位置 `~/.local/bin`）。不在 PATH 时用绝对路径
`~/.local/bin/mcode-theme`。

| 意图 | 命令 |
|---|---|
| 列出全部主题与当前主题 | `mcode-theme list` |
| 查看当前主题状态 | `mcode-theme current` |
| 切换主题 | `mcode-theme apply <name>` |
| 回落到 mcode 内置主题 | `mcode-theme restore` |
| 打开 Web 调色盘 | `mcode-theme web`（默认 http://localhost:8598） |
| 导入主题包 | `mcode-theme install <file.json\|url>` |
| 随机切一个 | `mcode-theme random` |

## 执行步骤

1. 把用户意图解析成上表里的一条命令。
2. 主题名不明确时，先跑 `mcode-theme list` 拿候选，再让用户选。
3. 执行命令。`apply` 会同时写入该主题的明暗两个变体并设置当前选中项。
4. 回报结果：主题名 + 是否生效。

## 失败处理

- `mcode-theme: command not found` → 改用绝对路径 `~/.local/bin/mcode-theme` 重试。
- `theme '<name>' not found` → 把 `mcode-theme list` 的输出给用户让他选。
- `端口 8598 已被占用` → 先 `ss -ltnp | grep 8598` 找出占用进程，或换 `--port 8599`。
- `主题文件 '<name>' 不存在` → 主题已被删除，重新 `mcode-theme apply <name>` 安装。
- apply 后界面没变化 → 确认 `mcode --version` ≥ 0.7.0；低版本没有原生主题机制。

## Windows (win32) platform notes

- 主题目录：`%USERPROFILE%\.minimax\tui\themes`
- 设置文件：`%USERPROFILE%\.minimax\tui\tui-settings.json`
- 命令是 `mcode-theme.cmd`；PowerShell 里执行
  `& "$env:USERPROFILE\.local\bin\mcode-theme.cmd" apply nord`
- Web 配置器端口同样是 8598，PowerShell 用 `Start-Process` 启动
