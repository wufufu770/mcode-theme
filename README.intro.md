# mcode-theme —— MiniMax Code CLI 主题定制工具

让每个 MiniMax Code 用户拥有自己的 mcode 配色。官方版本主题硬编码在 `cli.js` 里，
没有任何外部配置入口；本工具通过**安全补丁**替换主题色，一行命令换肤。

## 安装（不想装就…还是要装，因为要 patch 本机 cli.js）

```bash
cp mcode-theme ~/.local/bin/mcode-theme && chmod +x ~/.local/bin/mcode-theme
```

## 使用

```bash
mcode-theme list                 # 21 个内置主题：catppuccin / github-dark / claude-code / codex / kimi / minimax 官方 …
mcode-theme apply tokyo-night    # 一键换肤
mcode-theme plan synthwave       # Plan 模式主题：Shift+Tab 进出 Plan 自动切换配色
mcode-theme random               # 随机换肤
mcode-theme create my-theme      # 基于官方主题生成自定义模板
mcode-theme restore              # 随时恢复官方主题（自动备份原文件）
mcode-theme web                  # Web 可视化调色盘
```

## 效果

- **基础模式 / Plan 模式双主题**：正常界面用 A 主题，按 Shift+Tab 进入 Plan 模式
  自动切到 B 主题，退出自动切回，互不干扰
- **Web 调色盘**：浏览器里拖取色器实时调色，右侧实时预览 mcode 完整界面
  （Logo/边框/状态栏/对话气泡/代码块/Plan 徽标/输入框），Ctrl+S 一键写回
- **安全**：首次安装自动备份官方 cli.js；每次 patch 后自动做 JS 语法校验，
  破坏即回滚；mcode 升级覆盖后提示重新 apply

## 已知问题（当前版本）

- ⚠️ **Web 调色盘功能点尚未实测**：`mcode-theme web` 可启动并返回页面，
  但调色盘实时写回/保存主题的完整链路还没有经过真实浏览器验证
- ⚠️ **主题覆盖仍有 bug**：UI 配色已覆盖，但语法高亮、部分组件（如 Logo、
  状态栏图标）在个别主题下存在覆盖不完全的情况，正在修复中
- 截图待补充

## 关于"重复造轮子"

MiniMax 官方已宣布要构建 **插件体系 / TUI 扩展体系**，让每个用户都能自定义 mcode
（官方原话：相当于你可以自己 DIY 你的 TUI 的 UI，还可以通过插件给 Agent 加功能）。
mcode-theme 是在官方插件体系落地之前，用 cli.js 补丁方式先行实现的主题能力——
**很可能与官方后续推出的主题插件功能重叠**。届时本工具可以作为过渡方案，
或移植为官方插件体系下的一个主题插件（现有 21 个主题与 JSON 格式可直接复用）。

## 兼容性

- 已验证 mcode 0.1.1（主题应用函数 qsn / 状态栏 pon / chrome Bdn 三处钩子）
- 版本无关匹配：mcode 升级后若结构变化会明确报错提示，不会静默破坏

## 仓库

https://github.com/wufufu770/minimax-code-themes
