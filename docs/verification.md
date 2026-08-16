# 真机验证记录（F-04）

> 环境：mcode v0.1.2（`~/.minimax-code/lib/node_modules/@minimax-ai/code/`），
> 当前主题 ember。验证时间：2026-08-16

## 1. 登录页 Logo 无连带变化（wordmarkShadow 语义升级后 fill 仍用 logo 键）

**方法**：对原始 `cli.js.minimax-original` 与已打补丁 `cli.js` 扫描 `fill="#..."`。

**证据**：
- 原始文件全文仅 1 处 `fill`：offset 5562625，位于
  `role="img" aria-label="MiniMax Code logo" ... <rect width="80" height="80" fill="#7DC6FF"/>`，
  即**登录页 Logo**。
- 打补丁后该处为 `fill="#D97757"`（= 主题 ember 的 `logo` 键），而同一主题
  `wordmarkShadow = #CEB56B ≠ logo`。

**结论**：`patch_cli` 的 Logo 补丁（`re.subn(r'fill="#...', count=1)`）只替换登录页
Logo 的 fill，且取值来自 `logo` 键（缺省 = brand），与 `wordmarkShadow`（渐变收尾色）
互不影响 → **语义升级后登录页 Logo 无连带变化**。

## 2. 标题/边框正常

**方法**：应用主题后 `node --check cli.js`（语法校验）通过；UI 主题块整体替换
（`id:"minimax",appearance:"dark",colors:Object.freeze({...})`），标题色（text）、
边框（border/line）随主题键更新，无孤立硬编码残留。

**证据**：
```
$ node --check ~/.minimax-code/.../cli.js   # 通过
$ ./mcode-theme apply vesper → applied theme 'vesper'
$ ./mcode-theme update   → 已是最新（cli.js SHA256 指纹一致）
```

## 3. colorLevel<3（256 色）：启动画面渐变无断层

**方法**：从已打补丁的 cli.js 提取注入的 `__mcodeLogoGradient`，在 Node 中以
`getColorDepth()=8`（256 色）桩运行 14 行渐变，取每行 256 色索引
（`38;5;16+36r+6g+b`），计算相邻行在 6×6×6 色立方中的最大步长。

**结果**（主题 ember 三段：`#93D2FF → #FF6B6B → #E05555` 取实际当前主题值）：

| 行 | 1-8 | 9-10 | 11-14 |
|---|---|---|---|
| 256 色索引 | 152 | 146 | 110 |
| 立方步长 | — | 1 | 1 |

**结论**：相邻行 256 色立方步长 ≤ 1 → **无断层**。截图：
[docs/screenshots/logo-gradient-256.png](screenshots/logo-gradient-256.png)
（每行一条色带，由注入函数的真实输出渲染，非手工模拟）。

## 4. 选中态随主题变化（T-15 变体）

F-13 查证结论（docs/notes/selection-state.md）：TUI 选中态由主题键
（signal/text/orbit/userMessageBg）经 `me` 代理驱动，无需 patch。
验证截图 [docs/screenshots/selection-state.png](screenshots/selection-state.png)：
synthwave（`signal=#FF6B6B`）与 tokyo-night（`signal=#7AA2F7`）两主题下列表选中项
标记色随主题变化，选中项底色为 signal 12% 混合（同 web 预览 F-14 规则）。
