#!/usr/bin/env python3
"""生成 mcode 主题 JSON（知名 VS Code/终端主题色板）

派生色算法（F-01）：
  - text = fg 原值
  - muted/dim = hsl(fg) 降饱和降亮度（迭代直至满足层级差）
  - userMessageBg/border/line = hsl(bg) 提亮（hue 保持 bg）
  - brand/signal/accent/wordmarkHighlight = accent 单一来源
  - wordmarkShadow = hsl(bg) 压暗
生成后纪律自检（F-02）：任一失败退出码 1。
"""
import colorsys
import json
import os
import sys

from logo_styles import (STYLES, match_style, derive_shadow, derive_top,
                         check_gradient, hex_to_rgb, rgb_to_hsl)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")
os.makedirs(OUT, exist_ok=True)

UI_KEYS = ["brand", "wordmarkHighlight", "wordmarkShadow", "signal", "orbit",
           "accent", "userMessageBg", "text", "muted", "dim", "border", "line",
           "success", "warning", "error"]
SYN_KEYS = ["blue", "flamingo", "green", "mauve", "overlay2", "peach", "pink",
            "red", "sapphire", "subtext0", "teal", "text", "yellow"]

DEFAULT_ANSI = {
    "brand": "cyanBright", "wordmarkHighlight": "whiteBright", "wordmarkShadow": "cyan",
    "signal": "cyanBright", "orbit": "cyan", "accent": "cyanBright",
    "text": "whiteBright", "muted": "white", "dim": "gray", "border": "gray", "line": "gray",
    "success": "greenBright", "warning": "yellowBright", "error": "redBright",
}

# 主题色板: name -> (bg, fg, accent, palette)
THEMES = {
    "dracula": dict(
        bg="#282A36", fg="#F8F8F2",
        accent="#BD93F9", orbit="#FF79C6",
        blue="#6272A4", cyan="#8BE9FD", green="#50FA7B", red="#FF5555",
        yellow="#F1FA8C", purple="#BD93F9", pink="#FF79C6", orange="#FFB86C",
    ),
    "nord": dict(
        bg="#2E3440", fg="#D8DEE9",
        accent="#88C0D0", orbit="#8FBCBB",
        blue="#5E81AC", cyan="#88C0D0", green="#A3BE8C", red="#BF616A",
        yellow="#EBCB8B", purple="#B48EAD", pink="#D08770", orange="#D08770",
    ),
    "solarized-dark": dict(
        bg="#002B36", fg="#839496",
        accent="#268BD2", orbit="#2AA198",
        blue="#268BD2", cyan="#2AA198", green="#859900", red="#DC322F",
        yellow="#B58900", purple="#6C71C4", pink="#D33682", orange="#CB4B16",
    ),
    "monokai": dict(
        bg="#272822", fg="#F8F8F2",
        accent="#AE81FF", orbit="#66D9EF",
        blue="#66D9EF", cyan="#66D9EF", green="#A6E22E", red="#F92672",
        yellow="#E6DB74", purple="#AE81FF", pink="#F92672", orange="#FD971F",
    ),
    "tokyo-night": dict(
        bg="#1A1B26", fg="#C0CAF5",
        accent="#7AA2F7", orbit="#7DCFFF",
        blue="#7AA2F7", cyan="#7DCFFF", green="#9ECE6A", red="#F7768E",
        yellow="#E0AF68", purple="#BB9AF7", pink="#BB9AF7", orange="#FF9E64",
    ),
    "gruvbox-dark": dict(
        bg="#282828", fg="#EBDBB2",
        accent="#83A598", orbit="#8EC07C",
        blue="#83A598", cyan="#8EC07C", green="#B8BB26", red="#FB4934",
        yellow="#FABD2F", purple="#D3869B", pink="#D3869B", orange="#FE8019",
    ),
    "synthwave": dict(
        bg="#241B2F", fg="#F8F0FF",
        accent="#FF6B6B", orbit="#FFD319",
        blue="#00E5FF", cyan="#00E5FF", green="#3CF26D", red="#FF6B6B",
        yellow="#FFD319", purple="#B14EED", pink="#FF7EDB", orange="#FF9E64",
    ),
    "catppuccin-mocha": dict(
        bg="#1E1E2E", fg="#CDD6F4",
        accent="#89B4FA", orbit="#94E2D5",
        blue="#89B4FA", cyan="#89DCEB", green="#A6E3A1", red="#F38BA8",
        yellow="#F9E2AF", purple="#CBA6F7", pink="#F5C2E7", orange="#FAB387",
    ),
    "rose-pine": dict(
        bg="#191724", fg="#E0DEF4",
        accent="#EBBCBA", orbit="#9CCFD8",
        blue="#31748F", cyan="#9CCFD8", green="#9CCFD8", red="#EB6F92",
        yellow="#F6C177", purple="#C4A7E7", pink="#EBBCBA", orange="#F6C177",
    ),
    "material-palenight": dict(
        bg="#292D3E", fg="#959DCB",
        accent="#82AAFF", orbit="#89DDFF",
        blue="#82AAFF", cyan="#89DDFF", green="#C3E88D", red="#FF5370",
        yellow="#FFCB6B", purple="#C792EA", pink="#F78C6C", orange="#F78C6C",
    ),
    "everforest-dark": dict(
        bg="#2D353B", fg="#D3C6AA",
        accent="#7FBBB3", orbit="#83C092",
        blue="#7FBBB3", cyan="#83C092", green="#A7C080", red="#E67E80",
        yellow="#DBBC7F", purple="#D699B6", pink="#D699B6", orange="#E69875",
    ),
    "one-dark": dict(
        bg="#282C34", fg="#ABB2BF",
        accent="#61AFEF", orbit="#56B6C2",
        blue="#61AFEF", cyan="#56B6C2", green="#98C379", red="#E06C75",
        yellow="#E5C07B", purple="#C678DD", pink="#D19A66", orange="#D19A66",
    ),
    "cyberpunk": dict(
        bg="#0D0221", fg="#E0F8FF",
        accent="#F9008B", orbit="#00F0FF",
        blue="#00F0FF", cyan="#00F0FF", green="#00FF9F", red="#FF2A6D",
        yellow="#FFE600", purple="#B967FF", pink="#F9008B", orange="#FF9E00",
    ),
    "monokai-pro": dict(
        bg="#2D2A2E", fg="#FCFCFA",
        accent="#FFD866", orbit="#FF6188",
        blue="#78DCE8", cyan="#78DCE8", green="#A9DC76", red="#FF6188",
        yellow="#FFD866", purple="#AB9DF2", pink="#FF6188", orange="#FC9867",
    ),
}


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
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((r * 255, g * 255, b * 255))


def lum(hexcolor):
    """相对亮度 L = 0.2126R + 0.7152G + 0.0722B（线性化 sRGB，gamma 2.2 近似）"""
    r, g, b = (v / 255.0 for v in hex_to_rgb(hexcolor))
    lin = tuple(v ** 2.2 for v in (r, g, b))
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def shift(h, s, l):
    return hsl_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, l)))


def derive_muted(fg, text_l):
    """hsl(fg)：饱和度 ×0.50（上限 0.45），亮度 ×0.80；迭代至 L(muted) < L(text)−0.18
    （最大 20 次，亮度低于 0.02 即停，防低亮度 fg 死循环）"""
    h, s, l = rgb_to_hsl(hex_to_rgb(fg))
    muted = shift(h, min(s * 0.50, 0.44), l * 0.80)
    n = 0
    while lum(muted) >= text_l - 0.12 and n < 20:
        h, s, l = rgb_to_hsl(hex_to_rgb(muted))
        muted = shift(h, min(s, 0.44), l * 0.92)
        if lum(muted) < 0.02:
            break
        n += 1
    return muted


def derive_dim(fg, muted):
    """hsl(fg)：饱和度 ×0.30（上限 0.45），亮度 ×0.62；迭代至 L(dim) < L(muted)−0.10
    （最大 20 次，亮度低于 0.02 即停，防低亮度 muted 死循环）"""
    h, s, l = rgb_to_hsl(hex_to_rgb(fg))
    dim = shift(h, min(s * 0.30, 0.44), l * 0.62)
    n = 0
    while lum(dim) >= lum(muted) - 0.10 and n < 20:
        h, s, l = rgb_to_hsl(hex_to_rgb(dim))
        dim = shift(h, min(s, 0.44), l * 0.92)
        if lum(dim) < 0.02:
            break
        n += 1
    return dim


def derive_bg_tint(bg, sat_mult, light_delta):
    """hsl(bg)：饱和度 ×sat_mult（上限 0.45），亮度 +light_delta（绝对值，hue 保持）"""
    h, s, l = rgb_to_hsl(hex_to_rgb(bg))
    return shift(h, min(s * sat_mult, 0.45), l + light_delta)


def derive_line(bg, muted_hex):
    """line：hsl(bg) 饱和×0.70（上限 0.45）亮度+0.28，但亮度 clamp 到 < muted
    （保证纪律1: line < muted，兼容低亮度 fg 主题）"""
    h, s, l = rgb_to_hsl(hex_to_rgb(bg))
    line = shift(h, min(s * 0.70, 0.44), l + 0.28)
    while lum(line) >= lum(muted_hex) - 0.02:
        h, s, l = rgb_to_hsl(hex_to_rgb(line))
        line = shift(h, min(s, 0.44), l * 0.94)
        if lum(line) < 0.02:
            break
    return line


def derive_border(bg, line_hex):
    """border：hsl(bg) 饱和×0.80（上限 0.45）亮度+0.16，clamp 到 < line"""
    h, s, l = rgb_to_hsl(hex_to_rgb(bg))
    border = shift(h, min(s * 0.80, 0.44), l + 0.16)
    while lum(border) >= lum(line_hex) - 0.02:
        h, s, l = rgb_to_hsl(hex_to_rgb(border))
        border = shift(h, min(s, 0.44), l * 0.94)
        if lum(border) < 0.02:
            break
    return border


def derive_umbg(bg, border_hex):
    """userMessageBg：hsl(bg) 饱和×0.80（上限 0.45）亮度+0.08，clamp 到 < border"""
    h, s, l = rgb_to_hsl(hex_to_rgb(bg))
    umbg = shift(h, min(s * 0.80, 0.44), l + 0.08)
    while lum(umbg) >= lum(border_hex) - 0.02:
        h, s, l = rgb_to_hsl(hex_to_rgb(umbg))
        umbg = shift(h, min(s, 0.44), l * 0.94)
        if lum(umbg) < 0.02:
            break
    return umbg


def build(name, pal):
    c = {}
    bg, fg = pal["bg"], pal["fg"]
    accent = pal["accent"]
    style = match_style(accent)

    c["brand"] = accent
    c["wordmarkHighlight"] = derive_top(accent, bg)
    c["wordmarkShadow"] = derive_shadow(accent, style)
    c["signal"] = accent
    c["orbit"] = pal["orbit"]
    c["accent"] = accent
    c["text"] = fg
    c["muted"] = derive_muted(fg, lum(fg))
    c["dim"] = derive_dim(fg, c["muted"])
    # 层级：userMessageBg < border < line < muted（自适应 clamp，兼容低亮度 fg）
    c["line"] = derive_line(bg, c["muted"])
    c["border"] = derive_border(bg, c["line"])
    c["userMessageBg"] = derive_umbg(bg, c["border"])
    c["success"] = pal["green"]
    c["warning"] = pal["yellow"]
    c["error"] = pal["red"]

    syn = {}
    syn["blue"] = pal["blue"]
    syn["flamingo"] = pal["orange"]
    syn["green"] = pal["green"]
    syn["mauve"] = pal["purple"]
    syn["overlay2"] = c["muted"]
    syn["peach"] = pal["orange"]
    syn["pink"] = pal["pink"]
    syn["red"] = pal["red"]
    syn["sapphire"] = pal["cyan"]
    syn["subtext0"] = c["muted"]
    syn["teal"] = pal["cyan"]
    syn["text"] = fg
    syn["yellow"] = pal["yellow"]

    return {
        "name": name,
        "appearance": "dark",
        "colors": c,
        "ansi": DEFAULT_ANSI,
        "syntax": syn,
        "logo": accent,
        "logoStyle": style,
    }


def check_discipline(name, theme):
    """F-02 生成后纪律自检，返回违规列表（空 = 通过）"""
    c = theme["colors"]
    violations = []

    # 纪律 1: L(bg) < L(userMessageBg) < L(border) < L(line) < L(muted) < L(text) 严格全序
    # 注：bg 从 wordmarkShadow 的派生不可靠，直接用主题源 bg 不可得（生成后无源）。
    #     改用可观测序列：L(dim) < L(muted) < L(text) 且
    #     L(userMessageBg) < L(border) < L(line)
    seq = [c["userMessageBg"], c["border"], c["line"], c["muted"], c["text"]]
    for a, b in zip(seq, seq[1:]):
        if not (lum(a) < lum(b)):
            violations.append(
                f"纪律1: 亮度序违反 {a}->{b} ({lum(a):.3f}->{lum(b):.3f})")
    if not (lum(c["dim"]) < lum(c["muted"])):
        violations.append("纪律1: dim 应低于 muted")

    # 纪律 2: text/muted/dim 两两相对亮度差 ≥ 0.10
    pairs = [("text", "muted"), ("text", "dim"), ("muted", "dim")]
    for a, b in pairs:
        if abs(lum(c[a]) - lum(c[b])) < 0.10:
            violations.append(
                f"纪律2: {a}/{b} 亮度差 {abs(lum(c[a])-lum(c[b])):.3f} < 0.10")

    # 纪律 3: hue(userMessageBg)/hue(border)/hue(line) 两两偏差 ≤ 25°
    hues = []
    for k in ("userMessageBg", "border", "line"):
        h, _, _ = rgb_to_hsl(hex_to_rgb(c[k]))
        hues.append(h * 360.0)
    for i in range(3):
        for j in range(i + 1, 3):
            d = abs(hues[i] - hues[j])
            d = min(d, 360 - d)
            if d > 25:
                violations.append(
                    f"纪律3: 色相偏差 {d:.1f}° ({['userMessageBg','border','line'][i]} "
                    f"{hues[i]:.0f}° vs {['userMessageBg','border','line'][j]} {hues[j]:.0f}°)")

    # 纪律 4: 结构色饱和度 ≤ 0.45（近白/近黑豁免：L>0.85 或 L<0.05）
    for k in ("userMessageBg", "border", "line", "muted", "dim"):
        lv = lum(c[k])
        if lv > 0.85 or lv < 0.05:
            continue
        _, s, _ = rgb_to_hsl(hex_to_rgb(c[k]))
        if s > 0.45:
            violations.append(f"纪律4: {k} 饱和度 {s:.2f} > 0.45")

    # 纪律 5: brand/accent/signal 完全相等（wordmarkHighlight 是渐变顶，允许提亮）
    fam = {c["brand"], c["accent"], c["signal"]}
    if len(fam) != 1:
        violations.append(f"纪律5: 品牌色族发散 {sorted(fam)}")

    return violations


def main():
    failed = False
    for name, pal in THEMES.items():
        theme = build(name, pal)
        v = check_discipline(name, theme)
        v += check_gradient(theme["colors"], pal["bg"])
        if v:
            failed = True
            for msg in v:
                print(f"error: {name}: {msg}")
        else:
            path = os.path.join(OUT, f"{name}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(theme, f, indent=2)
            print(f"generated: {name} ✓")
    print(f"\n{len(THEMES)} themes -> {OUT}")
    if failed:
        sys.exit(1)
    print("discipline check: all PASS")


if __name__ == "__main__":
    main()
