#!/usr/bin/env python3
"""import-opencode.py — opencode 主题 → mcode 主题适配器

把 opencode 生态的主题 JSON（https://opencode.ai/theme.json schema，含 defs
引用）转换为 mcode 的 15 键 colors + 13 键 syntax 结构，并派生三段渐变 Logo。

用法：
  python3 import-opencode.py <主题.json> [--name X] [--appearance dark|light] [--out DIR]
  python3 import-opencode.py --all --out DIR    # 批量转换当前目录下所有 opencode 主题

退出码：
  0 = 成功（可能有 warning）
  1 = 转换失败（纪律 FAIL）
  2 = schema 无效
  3 = defs 循环引用
  4 = 缺少 primary 等必需键

许可：opencode 主题来自 anomalyco/opencode（MIT），转换逻辑本文件独立实现。
"""
import argparse
import colorsys
import json
import os
import sys

from logo_styles import (derive_shadow, derive_top, match_style,
                         check_gradient)

# ---------- 颜色工具 ----------


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


def shift(h, s, l):
    return hsl_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, l)))


def lum(hexcolor):
    r, g, b = (v / 255.0 for v in hex_to_rgb(hexcolor))
    lin = tuple(v ** 2.2 for v in (r, g, b))
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def is_hex(v):
    return isinstance(v, str) and v.startswith("#") and len(v) in (4, 7)


def normalize_hex(v):
    """3 位 hex → 6 位"""
    if isinstance(v, str) and v.startswith("#") and len(v) == 4:
        return "#" + "".join(ch * 2 for ch in v[1:])
    return v



def _tint(hx, sat_mult, light_delta):
    """bg 派生：hue 保持，饱和 ×sat_mult（上限 0.44），亮度 +light_delta"""
    h, s, l = rgb_to_hsl(hex_to_rgb(hx))
    return shift(h, min(s * sat_mult, 0.44), l + light_delta)


def lighten(hx, delta):
    h, s, l = rgb_to_hsl(hex_to_rgb(hx))
    return shift(h, s, l + delta)


def darken(hx, delta):
    h, s, l = rgb_to_hsl(hex_to_rgb(hx))
    return shift(h, s, l - delta)


# ---------- defs 展开（循环引用 → exit 3） ----------


def resolve_defs(theme, warnings, appearance="dark"):
    """递归展开 defs 引用，并按 appearance 选取 {dark,light} 双模式值。
    返回 theme 值全部为 #RRGGBB 的映射。"""
    defs = theme.get("defs") or {}
    raw = theme.get("theme") or {}
    if not isinstance(raw, dict):
        return {}

    def expand(value, stack):
        if is_hex(value):
            return value
        # 双模式对象 {dark:..., light:...}
        if isinstance(value, dict):
            pick = value.get(appearance) or value.get("dark") or value.get("light")
            if pick is None:
                warnings.append(f"无法选取双模式值 {value!r}")
                return None
            return expand(pick, stack)
        if isinstance(value, str) and value in defs:
            if value in stack:
                raise RuntimeError(f"defs 成环: {' -> '.join(stack + [value])}")
            ref = defs[value]
            if is_hex(ref):
                return ref
            return expand(ref, stack + [value])
        if isinstance(value, str) and value.startswith("#"):
            return value
        warnings.append(f"无法解析值 {value!r}")
        return None

    out = {}
    for k, v in raw.items():
        out[k] = normalize_hex(expand(v, []))
    return out


# ---------- F-05 映射表 ----------

DEFAULT_ANSI_DARK = {
    "brand": "cyanBright", "wordmarkHighlight": "whiteBright", "wordmarkShadow": "cyan",
    "signal": "cyanBright", "orbit": "cyan", "accent": "cyanBright",
    "text": "whiteBright", "muted": "white", "dim": "gray", "border": "gray", "line": "gray",
    "success": "greenBright", "warning": "yellowBright", "error": "redBright",
}
DEFAULT_ANSI_LIGHT = {
    "brand": "blueBright", "wordmarkHighlight": "blueBright", "wordmarkShadow": "blue",
    "signal": "blueBright", "orbit": "cyan", "accent": "blueBright",
    "text": "black", "muted": "black", "dim": "gray", "border": "gray", "line": "gray",
    "success": "green", "warning": "yellow", "error": "red",
}


def derive_muted(fg):
    h, s, l = rgb_to_hsl(hex_to_rgb(fg))
    muted = shift(h, min(s * 0.50, 0.44), l * 0.85)
    n = 0
    while lum(muted) >= lum(fg) - 0.12 and n < 20:
        h, s, l = rgb_to_hsl(hex_to_rgb(muted))
        muted = shift(h, min(s, 0.44), l * 0.92)
        if lum(muted) < 0.02:
            break
        n += 1
    return muted


def derive_dim(fg, muted):
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
    h, s, l = rgb_to_hsl(hex_to_rgb(bg))
    return shift(h, min(s * sat_mult, 0.44), l + light_delta)


def map_theme(th, warnings, appearance="dark"):
    is_light = appearance == "light"
    """按 F-05 映射表把 opencode theme 键转为 mcode colors + syntax。"""
    c, syn = {}, {}

    def get(*names, fallback=None):
        for n in names:
            if n in th and is_hex(th[n]):
                return th[n]
        return fallback

    # 必需键
    primary = get("primary")
    if primary is None:
        raise KeyError("primary")
    # opencode 的 accent 常与 primary 不同（如 ayu 蓝底黄 accent）；
    # mcode 纪律 5 要求 brand/accent/signal 单一来源 → 统一 primary，
    # opencode accent 降级为 orbit 次级强调。
    accent = primary
    text = get("text")
    if text is None:
        raise KeyError("text")
    bg = get("background") or "#11151C"
    bg_panel = get("backgroundPanel") or bg
    text_muted = get("textMuted")
    if text_muted is None:
        text_muted = derive_muted(text)
    border = get("border")
    border_subtle = get("borderSubtle") or border

    # colors
    c["brand"] = primary
    c["signal"] = get("signal") or primary
    c["accent"] = accent
    c["orbit"] = get("accent") or get("secondary") or get("info") or accent
    c["text"] = text
    if is_light:
        # light: 深字浅背景 → muted/dim 从 text 提亮（往浅色）
        c["muted"] = lighten(text, 0.20)
        c["dim"] = lighten(text, 0.34)
    else:
        c["muted"] = text_muted
        if lum(c["muted"]) < 0.15 or abs(lum(text) - lum(c["muted"])) < 0.12:
            c["muted"] = derive_muted(text)
        c["dim"] = get("dim") or darken(text_muted, 0.10)
    if abs(lum(c["muted"]) - lum(c["dim"])) < 0.10:
        h, s, l = rgb_to_hsl(hex_to_rgb(c["muted"]))
        c["dim"] = shift(h, min(s, 0.44), l * 0.60)
        n = 0
        while abs(lum(c["muted"]) - lum(c["dim"])) < 0.11 and n < 15:
            h, s, l = rgb_to_hsl(hex_to_rgb(c["dim"]))
            c["dim"] = shift(h, min(s, 0.44), l * 0.9)
            if lum(c["dim"]) < 0.02:
                break
            n += 1
    # 结构色从 bg_panel 派生（mcode 纪律要求 hue 收拢 220-245°；opencode 的
    # border/borderSubtle 常是同值或强调色，直接映射会违反纪律 1/3）
    # 饱和度 clamp ≤0.44 保证纪律 4；light 主题反向（line < border < umbg 递增）
    if is_light:
        c["userMessageBg"] = bg_panel
        c["border"] = _tint(bg_panel, 0.8, -0.16)
        c["line"] = _tint(bg_panel, 0.7, -0.24)
    else:
        c["userMessageBg"] = _tint(bg_panel, 0.8, 0.08)
        c["border"] = _tint(bg_panel, 0.8, 0.16)
        c["line"] = _tint(bg_panel, 0.7, 0.28)
    # 层级 clamp（带迭代上限，防近黑 bg 死循环）
    # dark:  umbg < border < line < muted（亮度递增）
    # light: muted < line < border < umbg（亮度递增）
    if not is_light:
        for _ in range(20):
            if lum(c["line"]) < lum(c["muted"]) - 0.02:
                break
            h, s, l = rgb_to_hsl(hex_to_rgb(c["line"]))
            c["line"] = shift(h, min(s, 0.44), l * 0.94)
        for _ in range(20):
            if lum(c["border"]) < lum(c["line"]) - 0.02:
                break
            h, s, l = rgb_to_hsl(hex_to_rgb(c["border"]))
            c["border"] = shift(h, min(s, 0.44), l * 0.94)
        for _ in range(20):
            if lum(c["userMessageBg"]) < lum(c["border"]) - 0.02:
                break
            h, s, l = rgb_to_hsl(hex_to_rgb(c["userMessageBg"]))
            c["userMessageBg"] = shift(h, min(s, 0.44), l * 0.94)
    else:
        for _ in range(20):
            if lum(c["muted"]) < lum(c["line"]) - 0.02:
                break
            h, s, l = rgb_to_hsl(hex_to_rgb(c["muted"]))
            c["muted"] = shift(h, min(s, 0.44), l * 1.06)
        for _ in range(20):
            if lum(c["line"]) < lum(c["border"]) - 0.02:
                break
            h, s, l = rgb_to_hsl(hex_to_rgb(c["line"]))
            c["line"] = shift(h, min(s, 0.44), l * 1.06)
        for _ in range(20):
            if lum(c["border"]) < lum(c["userMessageBg"]) - 0.02:
                break
            h, s, l = rgb_to_hsl(hex_to_rgb(c["border"]))
            c["border"] = shift(h, min(s, 0.44), l * 1.06)
    c["success"] = get("success") or "#28C567"
    c["warning"] = get("warning") or "#FFC340"
    c["error"] = get("error") or "#FF5E6C"
    # 三段渐变（F-03/F-04）
    style = match_style(primary)
    c["wordmarkHighlight"] = derive_top(primary)
    c["wordmarkShadow"] = derive_shadow(primary, style, c["userMessageBg"])

    # syntax
    syn["blue"] = get("syntaxFunction") or primary
    syn["mauve"] = get("syntaxKeyword") or accent
    syn["green"] = get("syntaxString") or c["success"]
    syn["peach"] = get("syntaxNumber") or c["warning"]
    syn["yellow"] = get("syntaxType") or c["warning"]
    syn["sapphire"] = get("syntaxOperator") or get("syntaxFunction") or primary
    syn["overlay2"] = get("syntaxComment") or derive_muted(c["muted"])
    syn["red"] = get("syntaxVariable") or c["error"]
    syn["teal"] = get("markdownLinkText") or get("syntaxOperator") or c["success"]
    syn["text"] = text
    syn["subtext0"] = text_muted
    # pink/flamingo: defs darkPink/darkFlamingo（若存在）
    pink = get("darkPink") or get("syntaxOperator") or accent
    flamingo = get("darkFlamingo") or get("syntaxPunctuation") or text
    syn["pink"] = pink
    syn["flamingo"] = flamingo

    return c, syn, style


# ---------- 纪律校验（与 validate-themes.py 同规格，含渐变 6-9） ----------

def check_discipline(colors, bg_hex=None, is_light=False):
    fails = []

    def L(k):
        return lum(colors[k]) if k in colors and is_hex(colors[k]) else -1

    if not is_light:
        seq1 = ["dim", "muted", "text"]
        for a, b in zip(seq1, seq1[1:]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1: 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
        seq2 = ["userMessageBg", "border", "line"]
        for a, b in zip(seq2, seq2[1:]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1: 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
    else:
        # 亮色主题反序
        seq1 = ["text", "muted", "dim"]
        for a, b in zip(seq1, seq1[1:]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1(light): 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
        seq2 = ["line", "border", "userMessageBg"]
        for a, b in zip(seq2, seq2[1:]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1(light): 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
    for a, b in [("text", "muted"), ("text", "dim"), ("muted", "dim")]:
        if abs(L(a) - L(b)) < 0.10:
            fails.append(f"纪律2: {a}/{b} 亮度差 {abs(L(a)-L(b)):.3f} < 0.10")
    hues = []
    for k in ("userMessageBg", "border", "line"):
        h, _, _ = rgb_to_hsl(hex_to_rgb(colors[k]))
        hues.append(h * 360.0)
    for i in range(3):
        for j in range(i + 1, 3):
            d = abs(hues[i] - hues[j])
            d = min(d, 360 - d)
            if d > 25:
                names = ["userMessageBg", "border", "line"]
                fails.append(f"纪律3: 色相偏差 {d:.1f}° ({names[i]} vs {names[j]})")
    for k in ("userMessageBg", "border", "line", "muted", "dim"):
        lv = L(k)
        if lv > 0.85 or lv < 0.05:
            continue
        _, s, _ = rgb_to_hsl(hex_to_rgb(colors[k]))
        if s > 0.45:
            fails.append(f"纪律4: {k} 饱和度 {s:.2f} > 0.45")
    fam = {colors["brand"], colors["accent"], colors["signal"]}
    if len(fam) != 1:
        fails.append(f"纪律5: 品牌色族发散 {sorted(fam)}")
    fails.extend(check_gradient(colors, bg_hex))
    return fails


def main(argv):
    ap = argparse.ArgumentParser(description="opencode 主题 → mcode 主题适配器")
    ap.add_argument("input", nargs="?", help="opencode 主题 JSON 路径")
    ap.add_argument("--name", default=None, help="输出主题名（默认取文件名）")
    ap.add_argument("--appearance", default="dark", choices=["dark", "light"])
    ap.add_argument("--out", default=os.path.expanduser("~/.minimax/themes"))
    ap.add_argument("--all", action="store_true", help="批量转换当前目录所有 *-opencode.json")
    ap.add_argument("--logo-style", default=None, help="强制指定渐变风格")
    args = ap.parse_args(argv)

    warnings = []
    files = []
    if args.all:
        for f in sorted(os.listdir(".")):
            if f.endswith("-opencode.json") or (f.endswith(".json") and not f.startswith(".")):
                files.append(f)
    elif args.input:
        files = [args.input]
    else:
        ap.print_help()
        return 2

    exit_code = 0
    for fn in files:
        try:
            with open(fn, "r", encoding="utf-8") as f:
                theme = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"error: 无法读取 {fn}: {e}", file=sys.stderr)
            return 2

        # 校验 schema（F-01）
        if theme.get("$schema") != "https://opencode.ai/theme.json":
            print(f"error: {fn} 不是 opencode theme（schema={theme.get('$schema')}）", file=sys.stderr)
            return 2

        name = args.name or os.path.splitext(os.path.basename(fn))[0]

        # defs 展开
        try:
            th = resolve_defs(theme, warnings, args.appearance)
        except RuntimeError as e:
            print(f"error: {fn}: {e}", file=sys.stderr)
            return 3

        # 映射（缺 primary/text → exit 4）
        try:
            colors, syn, style = map_theme(th, warnings, args.appearance)
        except KeyError as e:
            print(f"error: {fn}: 缺少必需键 {e}", file=sys.stderr)
            return 4

        out_theme = {
            "name": name,
            "appearance": args.appearance,
            "colors": colors,
            "ansi": DEFAULT_ANSI_DARK if args.appearance == "dark" else DEFAULT_ANSI_LIGHT,
            "syntax": syn,
            "logo": colors["accent"],
            "logoStyle": args.logo_style or style,
        }

        # 纪律校验（FAIL → exit 1，不产出）
        bg_ref = th.get("backgroundPanel") or th.get("background")
        fails = check_discipline(colors, bg_ref, args.appearance == 'light')
        for w in warnings:
            print(f"warning: {name}: {w}")
        if fails:
            print(f"error: {name}: 纪律未通过（未产出）")
            for f_ in fails:
                print(f"    - {f_}", file=sys.stderr)
            exit_code = 1
            continue

        os.makedirs(args.out, exist_ok=True)
        out_path = os.path.join(args.out, f"{name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_theme, f, indent=2, ensure_ascii=False)
        print(f"已输出: {out_path} (style={out_theme['logoStyle']})")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
