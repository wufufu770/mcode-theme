# 主题纪律验证报告（F-03）

> 由 `validate-themes.py` 全量运行 9 条纪律生成。生成时间：2026-08-16

| 主题 | 结果 | 纪律编号 | 说明 |
|---|---|---|---|
| aura | PASS | - |  |
| ayu-light | PASS | - |  |
| ayu | PASS | - |  |
| carbonfox | PASS | - |  |
| catppuccin-frappe-green | PASS | - |  |
| catppuccin-frappe | PASS | - |  |
| catppuccin-latte-blue | PASS | - |  |
| catppuccin-latte-mauve | PASS | - |  |
| catppuccin-macchiato-peach | PASS | - |  |
| catppuccin-macchiato | PASS | - |  |
| catppuccin-mocha | PASS | - |  |
| cobalt2 | PASS | - |  |
| cursor | PASS | - |  |
| cyberpunk | PASS | - |  |
| deepseek | PASS | - |  |
| dracula | PASS | - |  |
| ember | PASS | - |  |
| emerald | PASS | - |  |
| everforest-dark | PASS | - |  |
| flexoki | PASS | - |  |
| github-dark | PASS | - |  |
| gruvbox-dark | PASS | - |  |
| kanagawa | PASS | - |  |
| lucent-orng | PASS | - |  |
| material-palenight | PASS | - |  |
| material | PASS | - |  |
| matrix | PASS | - |  |
| mercury | PASS | - |  |
| minimax-light | PASS | - |  |
| minimax-official | PASS | - |  |
| monokai-pro | PASS | - |  |
| monokai | PASS | - |  |
| moonlight | PASS | - |  |
| nightowl | PASS | - |  |
| nord | PASS | - |  |
| one-dark | PASS | - |  |
| opencode | PASS | - |  |
| orng | PASS | - |  |
| osaka-jade | PASS | - |  |
| palenight | PASS | - |  |
| rose-pine | PASS | - |  |
| solarized-dark | PASS | - |  |
| synthwave-light | PASS | - |  |
| synthwave | PASS | - |  |
| tokyo-night | PASS | - |  |
| vercel | PASS | - |  |
| vesper | PASS | - |  |
| violet | PASS | - |  |
| zenburn-light | PASS | - |  |
| zenburn | PASS | - |  |

**总览：50/50 PASS，WARN 0，FAIL 0**

## 纪律说明

| 编号 | 规则 |
|---|---|
| 纪律0 | 必需颜色键齐全且为 #RRGGBB |
| 纪律1 | 亮度严格全序（dim < muted < text；userMessageBg < border < line；亮色主题反序） |
| 纪律2 | text/muted/dim 两两相对亮度差 ≥ 0.10 |
| 纪律3 | userMessageBg/border/line 色相两两偏差 ≤ 25° |
| 纪律4 | 结构色饱和度 ≤ 0.45 |
| 纪律5 | brand/accent/signal 完全相等 |
| 纪律6 | (R1) 渐变 mid/bottom 色相差 ≥60° 或明度差 ≥0.15 |
| 纪律7 | (R2) 渐变 top/mid 色相差 ≥30° 或明度差 ≥0.10 |
| 纪律8 | (R3) 渐变 bottom 与背景明度差 ≥0.08 或色相差 ≥30° |
| 纪律9 | (R4) 渐变三段两两颜色不同 |

纪律 6-9 无条件运行（即使纪律 1-5 存在 FAIL 也不跳过），保证渐变区分度恒被校验。
