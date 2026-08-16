# 选中态颜色来源查证（F-13）

> 结论先行：**mcode TUI 的列表/菜单选中态全部由主题键驱动**（经 `me` 代理读取当前
> 主题 colors 对象），无硬编码色、无 ANSI reverse 选中渲染 → **无需 patch**，
> 仅需 web 侧模拟（F-14）。

## 证据

### 1. `me` 是主题色只读代理（cli.js，v0.1.2）

```js
me=Object.freeze({
  get brand(){return aA.brand},
  get wordmarkHighlight(){return aA.wordmarkHighlight},
  get wordmarkShadow(){return aA.wordmarkShadow},
  get signal(){return aA.signal},
  get orbit(){return aA.orbit},
  get accent(){return aA.accent},
  get userMessageBg(){return aA.userMessageBg},
  get text(){return aA.text},
  get muted(){return aA.muted},
  get dim(){return aA.dim},
  get border(){return aA.border},
  ...  // 全部 15 键
})
```

`aA = jdn==="light"?snt.colors:ant.colors`，其中 `snt`/`ant` 即本工具 patch 的
`id:"minimax",appearance:"dark|light",colors:Object.freeze({...})` 主题块。
**所有选中态渲染都从 `me` 取色 → 主题改动（apply 新主题）会同步改变选中项颜色。**

### 2. 各列表/菜单选中态渲染（全部主题键，无一硬编码）

| 界面 | 函数 | 选中态样式 | 未选中样式 |
|---|---|---|---|
| Plan Review 选项 | `kgn` | `bold.signal("›") + bold.text(标签)` | `muted(标签)` |
| Plan 模式确认 | `Egn` render | `bold.signal("›") + bold.text/muted` | `muted` |
| 权限模式列表 | `dhl` | `bold.signal("›") + bold.text(标签)` + `signal("● active")` | 普通 `text` + `muted` |
| 更新对话框 | `HNn` | `bold.signal("› ...")` | `muted` |
| 插件列表 | `pfl` | `bold.signal(名称)` | `text(名称) + muted(描述)` |
| 历史提示 | `Kst` | `bold.signal("› ") + bold.text` | `muted` |
| 会话列表 | `agl`/`renderSessionLine` | `bold.signal("▌") + bold.text(标题)` | `dim("  ") + text(标题)` |
| 问卷单选 | `Ngn`/`Nst` | `bold.orbit(前缀) + bold.text + bgHex(userMessageBg)` | `text(前缀+标签) + muted(描述)` |
| 问卷步骤头 | `Pgn` render | `bold.orbit("●") + bold.text + bgHex(userMessageBg)` | `success("✓") / dim("○")` |
| Transcript 块 | `renderBlock` | `bold.signal("›") + bold.text(标题)` | `text(标题) + muted(摘要)` |
| 消息队列 | `Cgn` render | `"›" + text(行)` | `"  " + muted(行)` |

### 3. ANSI reverse 仅存在于 SGR 解析器，无选中渲染使用

cli.js 中 `inverse`（SGR 7）仅出现在样式库的解析分支：

```js
case 7:this.inverse=!0;break;   // 仅解码 \x1b[7m 控制序列
```

没有任何选中/高亮渲染器设置 `inverse` 或硬编码 ANSI 序列。

### 4. accent 键在 TUI 中的角色

`me.accent` 用于链接/代码/状态文本（如模型状态 `✓`、tool 输入标记、`+ Add custom
provider`），**不用于选中项背景**。选中标记统一用 `signal`（纪律 5 保证
brand==accent==signal，故选中标记颜色 = accent = brand，随主题变化）。

## 可控性结论

- 选中项**前景**（`›`/`▌` 标记与加粗标签）：`signal` / `text` / `orbit` —— 主题键
- 选中项**背景**（问卷等少数界面）：`userMessageBg` —— 主题键
- 全部经 `me` 代理动态读取 → **apply 主题后重启 mcode，选中项颜色随主题变化**

## 决策

依据 F-13 分支规则「若已用主题键 → 无需 patch，仅 web 侧模拟（F-14）」：
**本版本不实施 cli.js 选中态 patch**。web 预览的选中态模拟块（F-14）采用
`accent` 前景 + `accent 12%` 混合背景，与真实 TUI 的 signal==accent 语义一致。

## 验证方式（T-15 变体）

由于无需 patch，T-15 的验证改为：`apply synthwave` → 重启 mcode → 进入任一
列表（如 `/help` 或 Plan Review），选中项 `›` 标记为主题 signal 色；对比
`apply tokyo-night` 后同界面截图，标记色随主题变化。
