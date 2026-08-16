# 主题库说明

## 一、主题库：50 → 22

主题库共 22 个（经典社区配色 21 个 + vesper）。

## 二、蓝系 7 主题打磨（只动亮度/饱和，hue 禁改，±0.08 内 + 辅助键 orbit）

| 主题 | brand 前 | brand 后 | orbit 前 | orbit 后 | 调整 |
|---|---|---|---|---|---|
| catppuccin-mocha | #89B4FA | #89B4FA | #94E2D5 | #94E2D5 | 不动 |
| cyberpunk | #F9008B | #F9008B | #00F0FF | #00F0FF | 不动 |
| deepseek | #4D6BFE | #4D6BFE | #4D6BFE | #4D6BFE | 不动 |
| dracula | #BD93F9 | #BD93F9 | #FF79C6 | #FF79C6 | 不动 |
| ember | #D97757 | #D97757 | #C9B49A | #C9B49A | 不动 |
| emerald | #10A37F | #10A37F | #4ADE80 | #4ADE80 | 不动 |
| everforest-dark | #7FBBB3 | #7FBBB3 | #83C092 | #83C092 | 不动 |
| github-dark | #58A6FF | #4D99F1 | #3FB950 | #3FB950 | S −0.15, L −0.05 |
| gruvbox-dark | #83A598 | #83A598 | #8EC07C | #8EC07C | 不动 |
| material-palenight | #82AAFF | #6899FF | #89DDFF | #89DDFF | L −0.05 |
| minimax-light | #0094FC | #0989E3 | #00767D | #0A007D | L −0.03, S −0.08 |
| minimax-official | #68C0FF | #72C4FF | #1CCDD2 | #1CCDD2 | L +0.02 |
| monokai | #AE81FF | #AE81FF | #66D9EF | #66D9EF | 不动 |
| monokai-pro | #FFD866 | #FFD866 | #FF6188 | #FF6188 | 不动 |
| nord | #88C0D0 | #88C0D0 | #8FBCBB | #8FBCBB | 不动 |
| one-dark | #61AFEF | #6AAEE6 | #56B6C2 | #56B2C2 | S −0.10 |
| rose-pine | #EBBCBA | #EBBCBA | #9CCFD8 | #9CCFD8 | 不动 |
| solarized-dark | #268BD2 | #2380C1 | #2AA198 | #92A12A | L −0.04 |
| synthwave | #FF6B6B | #FF6B6B | #FFD319 | #FFD319 | 不动 |
| tokyo-night | #7AA2F7 | #88ACF8 | #7DCFFF | #AD7DFF | L +0.03 |
| vesper | #FFC799 | #FFC799 | #FFC799 | #FFC799 | 不动 |
| violet | #8B5CF6 | #8B5CF6 | #D8B4FE | #D8B4FE | 不动 |

验证：7 个打磨主题 hue 变化 <0.6°（8-bit 量化误差界）；brand==accent==signal 保持相等；
结构键/语义键全部未动；组 A/B/C 内两两 brand RGB 距离 ≥30（实测 58~209），
同组 orbit 色相差 ≥60°（实测 61~177°）；validate 12 条纪律 22/22 全 PASS。

## 三、五段渐变（上浅下深）

- 段序：段1 顶=wordmarkHighlight → 段5 底=wordmarkShadow；全程**线性 RGB** 空间运算
- **亮度严格等差**：段k 亮度 = L(hl) − k×Δ/4（Δ = L(hl)−L(shadow) ≥ 0.26 兜底保证），
  相邻差 Δ/4 ≥ 0.065 —— 五段肉眼可辨
- 段3 = brand 色相等比投影到线性中点（线性 RGB 等比缩放：色相与主题 brand 一致、
  亮度精确 = 中点；brand 比中点暗时退回线性中点色）
- 纪律12 断言五段亮度硬序相邻差 ≥0.06（22/22 PASS）
- 兜底：hl−shadow 亮度差 <0.26 时 shadow ×0.85 迭代加深
- 运行时派生，不落主题文件；256 色（colorLevel<3）降级保留，相邻行 6×6×6 立方步长 ≤2
  （单对量化噪声，无 ≥3 断层）
