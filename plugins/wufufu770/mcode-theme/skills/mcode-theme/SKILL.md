---
name: mcode-theme
description: MiniMax Code CLI 主题管理。当用户提到“主题/换主题/apply theme/切换主题/主题颜色/主题风格/恢复官方主题/主题可视化”时使用。
license: MIT
metadata:
  version: "0.3.0"
  category: productivity
---

# MiniMax Code CLI 主题管理

为 MiniMax Code CLI（mcode）提供主题安装、切换、恢复与可视化配置能力。
工具为独立 CLI 命令 `mcode-theme`（安装后位于 PATH，直接 bash 调用）。

## 前置

- 首次使用需一键安装（若 `mcode-theme` 命令不存在）：
  - 从 mcode-themes 仓库下载 `install.sh` 后执行 `bash install.sh`（默认装到 `~/.local/bin`，可用 `--prefix <目录>` 自定义）
- 需要 Python 3.8+；`mcode-theme apply` 后需重启 mcode 生效。

## 常用命令

```bash
mcode-theme list                      # 列出已安装主题与当前主题
mcode-theme apply <name>              # 应用主题（如 synthwave / tokyo-night）
mcode-theme restore                   # 回落到 mcode 内置默认主题
mcode-theme current                   # 当前主题状态（应用时间/生效状态）
mcode-theme update                    # 检测 mcode 是否升级
mcode-theme install <theme.json|URL>  # 校验（12 条纪律）并安装主题包
mcode-theme web                       # 启动 Web 可视化配置器 http://localhost:8598
```

## 使用流程

1. **应用主题**：`mcode-theme apply <name>` → **立即生效，无需重启**
   （mcode 监听主题目录并热重载）。
2. **恢复默认**：`mcode-theme restore` → 清除 `~/.minimax/tui/tui-settings.json` 的
   `theme` 字段，mcode 回落到内置主题（已安装的主题文件保留，便于再次 apply）。
3. **在线安装**：`mcode-theme install https://example.com/theme.json`，未通过 12 条纪律
   校验会拒绝并输出明细。
4. **可视化调色**：`mcode-theme web` 打开浏览器，改色实时预览，支持导出/导入主题包，
   头部状态卡显示当前主题的生效状态与 20 键色板。
5. **检测升级**：`mcode-theme update` 会提示 mcode 版本变化。

## 注意事项

- **mcode 0.7.0+ 走原生主题机制**：主题写入 `~/.minimax/tui/themes/<name>.json`，
  选中项写 `~/.minimax/tui/tui-settings.json`；**不再改写 `cli.js`**。
  mcode 0.7.0 的原生 schema 严格（UI 20 键 / 语法 13 键，`additionalProperties: false`），
  本工具会自动把 15 键旧主题补齐到 20 键。
- 主题库（可编辑源）在 `~/.local/share/mcode-themes/`，与 mcode 实际读取的
  `~/.minimax/tui/themes/` 分离。
- mcode 内置主题 id `minimax` / `midnight` / `graphite` / `aurora` 不可被同名文件覆盖。
- 22 个内置主题全部通过 validate-themes.py 12 条纪律校验（亮度全序/对比度/色相/
  饱和度/品牌色族/三段渐变/蓝系组内区分度/五段渐变亮度硬序）。
- 启动 Logo 为五段渐变（顶部亮→底部暗，运行时派生，256 色降级无断层）。
- Plan 模式：原生机制无 plan 钩子，`mcode-theme plan <name>` 退化为外观覆盖
  （`<id>/dark` 或 `<id>/light`）。

