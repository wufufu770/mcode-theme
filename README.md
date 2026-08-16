# mcode-theme

MiniMax Code CLI（mcode）主题管理工具：安装、切换、恢复主题，Web 可视化配置，
22 个内置主题，五段渐变 Logo。

## 功能

- **主题库**：22 个内置主题（经典社区配色）
- **一键应用/恢复**：`apply` 打补丁切换主题，`restore` 恢复官方默认
- **Web 可视化配置器**：实时预览、真实会话预览、主题包导出/导入、状态卡片
- **主题包**：JSON 格式分享/导入（格式校验 + 颜色键校验）
- **渐变 Logo**：五段垂直渐变（上浅下深），现代终端自动 truecolor，256 色降级
- **校验**：主题安装前自动校验（颜色亮度/色相/饱和度/对比度/渐变区分度）
- **升级检测**：`update` 检测 mcode 版本变化并提示重新应用

## 安装

```bash
bash install.sh                     # 默认安装到 ~/.local/bin（幂等，无需 sudo）
bash install.sh --prefix ~/bin      # 自定义目录
export PATH="$HOME/.local/bin:$PATH"
```

需要 Python 3.8+。

## 用法

```bash
mcode-theme apply <name>       # 应用主题
mcode-theme list               # 列出主题
mcode-theme current            # 当前主题状态（应用时间/生效状态/Plan 模式）
mcode-theme current --json     # 原始 JSON 输出
mcode-theme restore            # 恢复官方默认（自动清理配置）
mcode-theme update             # 检测 mcode 升级
mcode-theme install <theme.json|URL>   # 校验并安装主题
mcode-theme plan [<name>]      # Plan 模式主题（Shift+Tab 自动切换）
mcode-theme web                # Web 可视化配置器 → http://localhost:8598
```

> 说明：`install` 校验后入库（不自动应用），随后 `apply` 生效。`apply` 记录
> cli.js 指纹（`~/.minimax/themes/.last-applied.json`），供 `update` 检测升级。

## Web 配置器

- 6 大模块：UI 配色 / 代码语法高亮 / ANSI 8 色 / Plan 模式主题 / Logo / 字体
- 实时预览：模拟 mcode 界面，改动即时显示
- 真实会话预览：只读展示最近会话消息（每 3s 轮询）
- 主题包：导出/导入（校验 format + colors 15 键）
- 状态卡：当前主题 / Plan 主题，含 15 键色板
- 自定义下拉：主题切换 / Plan 主题 / 字体选择

## 主题库（22 个）

| 分组 | 数量 | 主题 |
|---|---|---|
| 经典主题 | 21 | catppuccin-mocha、cyberpunk、deepseek、dracula、ember、emerald、everforest-dark、github-dark、gruvbox-dark、material-palenight、minimax-light、minimax-official、monokai-pro、monokai、nord、one-dark、rose-pine、solarized-dark、synthwave、tokyo-night、violet |
| 其他 | 1 | vesper |

全部主题通过校验（docs/validation-report.md）。

### 渐变 Logo

mcode 启动 Logo 使用五段垂直渐变（顶部亮 → 底部暗）：
- 段1 = `wordmarkHighlight`，段3 = `brand`，段5 = `wordmarkShadow`（主题三键原色）
- 段2/段4 为 RGB 线性插值
- 现代终端（Termius、Windows Terminal、iTerm2、GNOME Terminal 等）自动 24bit
  truecolor；256 色终端降级为五段色块（去重保证可辨）
- 运行时派生，不落主题文件

## 校验规则

`validate-themes.py` 对主题执行 13 项检查（亮度全序、对比度、色相一致性、
饱和度、品牌色族、渐变区分度、蓝系组内区分度、五段渐变亮度序）：
```bash
python3 validate-themes.py [目录]   # 默认 ./themes
```

## 转换器

```bash
python3 import-opencode.py 主题.json --name X --out ~/.minimax/themes
python3 import-pi.py pi主题.json --out ~/.minimax/themes
```

## 主题格式

主题 JSON 位于 `~/.minimax/themes/<name>.json`：

```json
{
  "name": "synthwave",
  "appearance": "dark",
  "colors": {
    "brand": "#FF6B6B", "accent": "#FF6B6B", "signal": "#FF6B6B",
    "wordmarkHighlight": "#FF9494", "wordmarkShadow": "#966911",
    "orbit": "#FFD93D", "userMessageBg": "#2A1E3F",
    "text": "#F8F0FF", "muted": "#B8A8D8", "dim": "#8A7BA8",
    "border": "#4A3A6A", "line": "#8A7BA8",
    "success": "#4ADE80", "warning": "#FFC340", "error": "#FF5E6C"
  }
}
```

## 许可

MIT — 见 LICENSE。
