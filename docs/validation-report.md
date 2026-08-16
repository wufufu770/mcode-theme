# 主题纪律验证报告（22 主题）

> 由 `validate-themes.py` 全量运行 13 条纪律（0-12）生成。生成时间：2026-08-16

| 主题 | 结果 | 纪律编号 | 说明 |
|---|---|---|---|
| catppuccin-mocha | PASS | - |  |
| cyberpunk | PASS | - |  |
| deepseek | PASS | - |  |
| dracula | PASS | - |  |
| ember | PASS | - |  |
| emerald | PASS | - |  |
| everforest-dark | PASS | - |  |
| github-dark | PASS | - |  |
| gruvbox-dark | PASS | - |  |
| material-palenight | PASS | - |  |
| minimax-light | PASS | - |  |
| minimax-official | PASS | - |  |
| monokai-pro | PASS | - |  |
| monokai | PASS | - |  |
| nord | PASS | - |  |
| one-dark | PASS | - |  |
| rose-pine | PASS | - |  |
| solarized-dark | PASS | - |  |
| synthwave | PASS | - |  |
| tokyo-night | PASS | - |  |
| vesper | PASS | - |  |
| violet | PASS | - |  |

**总览：22/22 PASS，WARN 0，FAIL 0**

## 纪律说明

| 编号 | 规则 |
|---|---|
| 纪律0 | 必需颜色键齐全且为 #RRGGBB |
| 纪律1 | 亮度严格全序（暗色/亮色分别正/反序） |
| 纪律2 | text/muted/dim 两两相对亮度差 ≥ 0.10 |
| 纪律3 | userMessageBg/border/line 色相两两偏差 ≤ 25° |
| 纪律4 | 结构色饱和度 ≤ 0.45 |
| 纪律5 | brand/accent/signal 完全相等 |
| 纪律6 | (R1) 渐变 mid/bottom 色相差 ≥60° 或明度差 ≥0.15 |
| 纪律7 | (R2) 渐变 top/mid 色相差 ≥30° 或明度差 ≥0.10 |
| 纪律8 | (R3) 渐变 bottom 与背景明度差 ≥0.08 或色相差 ≥30° |
| 纪律9 | (R4) 渐变三段两两颜色不同 |
| 纪律10 | 蓝系组 A/B/C 内两两 brand RGB 距离 ≥30 |
| 纪律11 | 蓝系同组 orbit 色相差 ≥60° |
| 纪律12 | 五段渐变亮度硬序 L1>L2>L3>L4>L5 相邻差 ≥0.06 |

纪律 6-12 无条件运行（即使纪律 1-5 存在 FAIL 也不跳过）。
