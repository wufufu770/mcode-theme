#!/usr/bin/env python3
"""logo_styles.py — 三段渐变风格库（F-04）

经典三段渐变风格的派生逻辑。用于 gen-themes.py / import-opencode.py /
import-pi.py 的 wordmarkShadow（渐变收尾色）与 wordmarkHighlight 派生。

规则（F-02 三段区分度硬规则）：
  R1: mid 与 bottom 色相差 ≥60° 或明度差 ≥0.15
  R2: top 与 mid 色相差 ≥30° 或明度差 ≥0.10
  R3: bottom 与背景 bg 明度差 ≥0.08 或色相差 ≥30°
  R4: 三段两两颜色不同

风格库（8 套）：每个风格定义 bottom 色相对 mid(accent) hue 的偏移与亮度范围。
"""
import colorsys

STYLES = {
    "ai-blue-purple": {"label": "AI 蓝紫粉", "delta": 90, "l_min": 0.55, "l_max": 0.65, "desc": "蓝→紫→粉"},
    "tech-cyan-blue": {"label": "科技青蓝紫", "delta": 70, "l_min": 0.55, "l_max": 0.65, "desc": "青→蓝→紫"},
    "synthwave": {"label": "Synthwave", "delta": 90, "l_min": 0.50, "l_max": 0.62, "desc": "粉→紫→蓝", "top_delta": -40},
    "flame": {"label": "火焰", "delta": 40, "l_min": 0.55, "l_max": 0.70, "desc": "红→橙→黄"},
    "matrix": {"label": "Matrix", "delta": 80, "l_min": 0.50, "l_max": 0.62, "desc": "绿→黄绿→黄"},
    "emerald": {"label": "翡翠", "delta": 30, "l_min": 0.55, "l_max": 0.68, "desc": "绿→青→天蓝"},
    "high-impact": {"label": "高冲击", "delta": 60, "l_min": 0.55, "l_max": 0.68, "desc": "紫→粉→橙"},
    "nord": {"label": "Nord", "delta": -60, "l_min": 0.55, "l_max": 0.68, "desc": "青→蓝→靛"},
}

STYLE_ORDER = ["ai-blue-purple", "tech-cyan-blue", "synthwave", "flame",
               "matrix", "emerald", "high-impact", "nord"]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def rgb_to_hsl(rgb):
    r, g, b = (v / 255.0 for v in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def hsl_to_rgb(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, l, s)
    return rgb_to_hex((r * 255, g * 255, b * 255))


def lum(hexcolor):
    r, g, b = (v / 255.0 for v in hex_to_rgb(hexcolor))
    lin = tuple(v ** 2.2 for v in (r, g, b))
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def hue_of(hexcolor):
    h, _, _ = rgb_to_hsl(hex_to_rgb(hexcolor))
    return h * 360.0


def _hue_diff(a, b):
    d = abs(a - b)
    return min(d, 360 - d)


def _derive_style_bottom(accent_hex, style, attempt=0):
    """按风格派生 bottom 色。attempt 递增旋转 hue 直至满足 R1（与 mid 色相差 ≥60° 或明度差 ≥0.15）。"""
    st = STYLES[style]
    h, s, l = rgb_to_hsl(hex_to_rgb(accent_hex))
    delta = st["delta"] + attempt * 20
    l_target = st["l_min"] + (st["l_max"] - st["l_min"]) * 0.5
    bottom = hsl_to_rgb(h + delta / 360.0, max(0.25, min(0.85, s * 0.8)), l_target)
    # 循环尝试：至多 6 次
    for i in range(6):
        bh = hue_of(bottom)
        if _hue_diff(bh, h * 360.0) >= 60 or abs(lum(bottom) - lum(accent_hex)) >= 0.15:
            break
        bottom = hsl_to_rgb(h + (delta + (i + 1) * 25) / 360.0,
                            max(0.25, min(0.85, s * 0.8)), l_target * (1.0 + 0.05 * i))
    return bottom


def derive_top(accent_hex, bg_hex=None):
    """top = hsl(accent, l+0.08)；若与 mid 色相差 <30° 且明度差 <0.10，则色相 −35°（留边界余量）"""
    h, s, l = rgb_to_hsl(hex_to_rgb(accent_hex))
    top = hsl_to_rgb(h, s, l + 0.08)
    if _hue_diff(hue_of(top), hue_of(accent_hex)) < 30 and abs(lum(top) - lum(accent_hex)) < 0.10:
        top = hsl_to_rgb(h - 35 / 360.0, s, l + 0.12)
    # R4: 禁止同 HEX
    if top.upper() == accent_hex.upper():
        h2, s2, l2 = rgb_to_hsl(hex_to_rgb(top))
        top = hsl_to_rgb(h2 + 15 / 360.0, s2, l2 + 0.10)
    return top


def derive_shadow(accent_hex, style=None, bg_hex=None):
    """bottom = 按风格派生（F-04），style=None 时自动选择最接近的风格。
    bg_hex 提供时保证 R3（bottom 与 bg 明度差 ≥0.08 或色相差 ≥30°），
    且迭代全程保持 R1（与 mid 色相差 ≥60° 或明度差 ≥0.15）。"""
    if style is None:
        style = match_style(accent_hex)
    bottom = _derive_style_bottom(accent_hex, style)
    mid_h = hue_of(accent_hex)
    for i in range(8):
        r1_ok = _hue_diff(hue_of(bottom), mid_h) >= 60 or abs(lum(bottom) - lum(accent_hex)) >= 0.15
        r3_ok = True
        if bg_hex:
            r3_ok = abs(lum(bottom) - lum(bg_hex)) >= 0.08 or _hue_diff(hue_of(bottom), hue_of(bg_hex)) >= 30
        if r1_ok and r3_ok:
            break
        h, s, l = rgb_to_hsl(hex_to_rgb(bottom))
        if not r3_ok:
            bottom = hsl_to_rgb(h, s, min(1.0, l + 0.07 * (i + 1)))
        elif not r1_ok:
            bottom = hsl_to_rgb(h + 25 / 360.0, s, l)
    return bottom


def match_style(accent_hex):
    """选择 bottom hue 与 (accent hue + 风格偏移) 最接近的风格。"""
    ah = hue_of(accent_hex)
    best, best_score = STYLE_ORDER[0], 1e9
    for name in STYLE_ORDER:
        st = STYLES[name]
        target = ah + st["delta"]
        target %= 360
        score = min(abs(target - ah), 360 - abs(target - ah)) + abs(target - ah) * 0.01
        score = _hue_diff(target, ah) + abs(_hue_diff(target, 0) - _hue_diff(ah, 0)) * 0.01
        # 更简单的匹配：风格 bottom 与 accent 的距离
        test_bottom = _derive_style_bottom(accent_hex, name)
        dist = _hue_diff(hue_of(test_bottom), ah)
        if dist < best_score:
            best_score = dist
            best = name
    return best


def check_gradient(colors, bg_hex):
    """F-02 纪律 6-9：三段渐变区分度。返回违规列表（空=通过）。"""
    v = []
    top, mid, bottom = colors["wordmarkHighlight"], colors["brand"], colors["wordmarkShadow"]
    th, tm, tb = hue_of(top), hue_of(mid), hue_of(bottom)
    # R1: mid vs bottom
    if _hue_diff(tm, tb) < 60 and abs(lum(mid) - lum(bottom)) < 0.15:
        v.append(f"纪律6(R1): mid/bottom 色相差 {_hue_diff(tm,tb):.0f}° <60 且明度差 {abs(lum(mid)-lum(bottom)):.2f} <0.15")
    # R2: top vs mid
    if _hue_diff(th, tm) < 30 and abs(lum(top) - lum(mid)) < 0.10:
        v.append(f"纪律7(R2): top/mid 色相差 {_hue_diff(th,tm):.0f}° <30 且明度差 {abs(lum(top)-lum(mid)):.2f} <0.10")
    # R3: bottom vs bg
    if bg_hex:
        if abs(lum(bottom) - lum(bg_hex)) < 0.08 and _hue_diff(tb, hue_of(bg_hex)) < 30:
            v.append(f"纪律8(R3): bottom/bg 明度差 {abs(lum(bottom)-lum(bg_hex)):.2f} <0.08 且色相差 <30°")
    # R4: 两两不同
    if top.upper() == mid.upper():
        v.append("纪律9(R4): top == mid 同色")
    if mid.upper() == bottom.upper():
        v.append("纪律9(R4): mid == bottom 同色")
    if top.upper() == bottom.upper():
        v.append("纪律9(R4): top == bottom 同色")
    return v
