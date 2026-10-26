# mcode-theme

MiniMax Code CLI（mcode）主题管理工具：安装、切换、恢复主题，Web 可视化配置，
22 个内置主题，五段渐变 Logo。

## 功能

- **主题库**：22 个内置主题（经典社区配色）
- **一键应用/恢复**：`apply` 切换主题，`restore` 回落到 mcode 内置默认
- **Web 可视化配置器**：实时预览、真实会话预览、主题包导出/导入、状态卡片
- **主题包**：JSON 格式分享/导入（格式校验 + 颜色键校验）
- **渐变 Logo**：五段垂直渐变（上浅下深），现代终端自动 truecolor，256 色降级
- **校验**：主题安装前自动校验（颜色亮度/色相/饱和度/对比度/渐变区分度）
- **升级检测**：`update` 检测 mcode 版本变化并提示重新应用

> **v0.3.0 起基于 mcode 0.7.0 的原生主题机制**（不再改写 `cli.js`），
> 详见「mcode 0.7.0 原生主题机制」。旧版 mcode（< 0.7.0）仍走打补丁的老路径。

## CLI 内热切换（/theme）

mcode 0.7.0 自带 `/theme` 命令，会扫描 `~/.minimax/tui/themes/` 并列出**全部自定义主题**，
选中即热切换（mcode 监听该目录，无需重启）。本工具的应用动作就是往这个目录里写文件，
所以**不需要插件、不需要重启**：

```
/theme            → 列表里能看到 22 个自定义主题 + 4 个内置主题
                   （←/→ 可切 auto / light / dark 外观，Enter 保存）
```

> **为什么没有做成 `/mcode-theme` 自定义命令？**
> mcode 的两种插件格式都不支持注册命令：`AGENT_PLUGINS_V1` 的 `plugin.json`
> 白名单只有 `skills` / `mcpServers` / `hooks` / `apps` / `extensions`，
> `MINIMAX` 格式的 `.minimax-plugin/plugin.json` 白名单里也没有 `commands`。
> 代码里唯一的命令注入点是 `commandContributions`（由嵌入宿主传入），
> ACP 与 app-server 协议均未暴露该通道。所以 `/theme` + 自定义主题目录
> 就是官方支持的扩展路径。

主题带 `label` / `description` 时，选择器会显示友好名称与 About 说明；
同一主题的明暗两个变体（同名 + 不同 `appearance`）会被 mcode 合并成一条，
用 ←/→ 即可切换外观。

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

## 明暗变体

`gen-light-variants.py` 从 dark 主题派生配套的 light 变体：

- 中性色（text/muted/dim/border/line）按**角色目标明度**重映射，同时保留原色相
  → 每个主题的浅色版仍有自己的味道，又符合浅底可读性约定
- 强调色用**单调线性明度映射** → 保持 brand / wordmarkHighlight 之间的对比关系
- 自动对比度兜底：强调色在浅底上至少 3:1（WCAG AA）
- 实测 21 个主题的浅色版正文对比度 8.8:1 ~ 10.9:1

```bash
python3 gen-light-variants.py [themes目录]      # 生成 <name>.light.json
python3 theme-metadata.py [themes目录]           # 补 label / description
```

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

### 主题库格式（mcode-theme 自有，可编辑源）

装在 `~/.local/share/mcode-themes/<name>.json`，是 Web 配置器的编辑对象，
比 mcode 原生 schema 多两个键（`ansi` 降级色、`logo` / `logoStyle`）：

```json
{
  "name": "synthwave",
  "appearance": "dark",
  "colors": { "brand": "#FF6B6B", "...": "..." },
  "ansi":   { "brand": "cyanBright", "...": "..." },
  "syntax": { "blue": "#89B4FA", "...": "..." },
  "logo": "#FF6B6B"
}
```

### mcode 原生格式（mcode 实际读取）

`mcode-theme apply` 会把主题库转换成 mcode 原生 schema，写到
**`~/.minimax/tui/themes/<name>.json`** —— 这是 mcode 0.7.0 扫描的目录，
schema 严格（`additionalProperties: false`），多一个键就会被 mcode 拒绝。

```json
{
  "name": "synthwave",
  "appearance": "dark",
  "colors": {
    "brand": "#FF6B6B", "wordmarkHighlight": "#FF9494", "wordmarkShadow": "#966911",
    "signal": "#FF6B6B", "orbit": "#FFD93D", "accent": "#FF6B6B",
    "markdownHeading": "#CBA6F7", "markdownCode": "#A6E3A1", "markdownLink": "#89B4FA",
    "userMessageBg": "#2A1E3F", "diffAddedBg": "#3A2F44", "diffRemovedBg": "#452A3A",
    "text": "#F8F0FF", "muted": "#B8A8D8", "dim": "#8A7BA8",
    "border": "#4A3A6A", "line": "#8A7BA8",
    "success": "#4ADE80", "warning": "#FFC340", "error": "#FF5E6C"
  },
  "syntax": { "blue": "#89B4FA", "...": "..." }
}
```

- UI 键 **20 个**（mcode 0.7.0 新增 `markdownHeading` / `markdownCode` /
  `markdownLink` / `diffAddedBg` / `diffRemovedBg`），语法键 **13 个**
- 主题库里的旧主题没有这 5 个新键，转换时从主题自身调色板派生：
  `markdownHeading ← syntax.mauve`、`markdownCode ← syntax.green`、
  `markdownLink ← syntax.blue`、`diffAddedBg/diffRemovedBg ← success/error 混色`
- 主题名必须匹配 `^[a-z0-9][a-z0-9._-]{0,63}$`；`minimax` / `midnight` /
  `graphite` / `aurora` 是 mcode 内置 id，同名自定义文件会被忽略

## mcode 0.7.0 原生主题机制

mcode 0.7.0 起内置了主题系统，本工具**不再改写 `cli.js`**：

| 概念 | 位置 |
|---|---|
| 自定义主题文件 | `~/.minimax/tui/themes/*.json` |
| 当前选中项 | `~/.minimax/tui/tui-settings.json` → `{"theme": "<id>"}` |
| 外观覆盖 | `{"theme": "<id>/dark"}` 或 `{"theme": "<id>/light"}` |
| 内置主题 | `minimax` / `midnight` / `graphite` / `aurora`（另有 `/theme` 命令切换） |
| 本工具元数据 | `~/.minimax/mcode-theme/`（放在 themes/ 外，避免被 mcode 扫描） |

mcode 监听 `themes/` 目录并热重载，**切换主题无需重启**。

`mcode-theme restore` = 清除 `tui-settings.json` 的 `theme` 字段，mcode 回落到内置主题。

## 许可

MIT — 见 LICENSE。

## 版本历史

### v0.3.0 (2026-10-26)
- **适配 mcode 0.7.0 原生主题机制**：不再改写 `cli.js`，改为写
  `~/.minimax/tui/themes/*.json` + 设置 `tui-settings.json`
- 支持 mcode 0.7.0 新增的 5 个 UI 键（markdown / diff），旧主题自动派生
- 主题库与原生目录分离：`~/.local/share/mcode-themes/`（可编辑源）↔
  `~/.minimax/tui/themes/`（mcode 读取）
- Web 配置器改用原生写入，支持实时预览与热重载

### v0.1.6 (2026-08-19)
- 适配 mcode v0.1.6
- 主题应用功能正常

### v0.1.4
- 适配 mcode v0.1.4
- 添加 logo 渐变插桩
