#!/usr/bin/env python3
"""import-pi.py — pi-agent 主题 → mcode 主题适配器

把 pi-agent 生态的主题 JSON（Catppuccin / Dracula / Tokyo Night 等，含 vars
引用与 256 色索引）转换为 mcode 的 15 键 colors + 13 键 syntax 结构。

用法：
  python3 import-pi.py <pi主题.json> [--name 输出名] [--appearance dark|light] [--out 输出目录]

默认 --out ~/.minimax/themes/，--name 缺省取 pi 主题的 name 字段。

行为边界：
  - pi 主题缺 name 或缺 colors 键 → exit 2，不产出文件
  - vars 引用成环 → exit 3
  - 无法解析的颜色值 → 警告并回退派生，不中断
  - 输出前用主题纪律校验过滤；FAIL 打印 warning 并继续输出，exit 0

退出码：0 = 成功（可能带 warning），2 = 输入结构错误，3 = vars 成环。
"""
import colorsys
import json
import os
import sys

# ---------- 颜色工具 ----------

# 标准 xterm 256 色表（0-255 → #RRGGBB）
def _xterm256():
    table = {}
    # 0-15 系统色（标准 xterm 值）
    sys_colors = [
        "#000000", "#800000", "#008000", "#808000",
        "#000080", "#800080", "#008080", "#C0C0C0",
        "#808080", "#FF0000", "#00FF00", "#FFFF00",
        "#0000FF", "#FF00FF", "#00FFFF", "#FFFFFF",
    ]
    for i, c in enumerate(sys_colors):
        table[i] = c
    # 16-231: 6×6×6 立方体
    levels = [0, 95, 135, 175, 215, 255]
    idx = 16
    for r in levels:
        for g in levels:
            for b in levels:
                table[idx] = "#%02X%02X%02X" % (r, g, b)
                idx += 1
    # 232-255: 灰阶
    for i in range(24):
        v = 8 + i * 10
        table[232 + i] = "#%02X%02X%02X" % (v, v, v)
    return table


XTERM256 = _xterm256()


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
    return isinstance(v, str) and v.startswith("#") and len(v) == 7


def parse_color(v):
    """解析颜色值：支持 #RRGGBB、256 色整数索引、命名色（见 pi 生态）"""
    if is_hex(v):
        return v
    if isinstance(v, int) and 0 <= v <= 255:
        return XTERM256[v]
    # 常用命名色兜底
    named = {
        "black": "#000000", "white": "#FFFFFF", "red": "#FF0000",
        "green": "#008000", "blue": "#0000FF", "yellow": "#FFFF00",
        "magenta": "#FF00FF", "cyan": "#00FFFF", "gray": "#808080",
        "grey": "#808080", "transparent": None,
    }
    if isinstance(v, str) and v.lower() in named:
        return named[v.lower()]
    return None


def derive_muted(fg, text_l=None):
    text_l = lum(fg) if text_l is None else text_l
    h, s, l = rgb_to_hsl(hex_to_rgb(fg))
    muted = shift(h, min(s * 0.50, 0.44), l * 0.85)
    n = 0
    while lum(muted) >= text_l - 0.12 and n < 20:
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


# ---------- vars 展开 ----------

def resolve_vars(theme, warnings):
    """递归展开 vars 引用。pi 生态两种引用形态：
    1. `vars.<name>` 前缀引用
    2. 裸 vars 键名（colors 值直接是 vars 的 key，如 'mauve'）
    返回 (colors, vars) 或抛出 RuntimeError（成环）。"""
    vars_map = theme.get("vars") or {}
    colors = theme.get("colors") or {}

    def is_var_ref(value):
        if not isinstance(value, str):
            return False
        s = value.strip()
        if s.startswith("vars."):
            return True
        return s in vars_map

    def var_name(value):
        s = value.strip()
        return s[len("vars."):] if s.startswith("vars.") else s

    def expand(value, stack):
        if not is_var_ref(value):
            return value
        name = var_name(value)
        if name in stack:
            raise RuntimeError(f"vars 成环: {' -> '.join(stack + [name])}")
        if name not in vars_map:
            warnings.append(f"未知 vars 引用: {name}，回退原始值")
            return value
        ref = vars_map[name]
        if is_var_ref(ref):
            return expand(ref, stack + [name])
        return ref

    out_colors = {}
    for k, v in colors.items():
        out_colors[k] = expand(v, [])
    out_vars = {}
    for k, v in vars_map.items():
        out_vars[k] = expand(v, [])
    return out_colors, out_vars


# ---------- pi schema → mcode 映射（F-05） ----------

def map_theme(pi_colors, pi_vars, warnings, appearance="dark"):
    """按 F-05 映射表把 pi colors/vars 转为 mcode colors + syntax。"""
    c = {}
    syn = {}

    def get(*names, fallback=None):
        for n in names:
            if n in pi_colors and is_hex(pi_colors[n]):
                return pi_colors[n]
            if n in pi_vars and is_hex(pi_vars[n]):
                return pi_vars[n]
        return fallback

    # 基准色
    text = get("text", fallback="#E6E9EF")
    fg = text
    bg = get("bg", "background", fallback="#11151C")
    accent = get("accent", fallback=text)
    orbit = get("borderAccent", "mdLink", fallback=accent)

    # colors 映射
    c["text"] = text
    muted = get("muted")
    if muted is None:
        muted = derive_muted(fg)
        warnings.append("colors.muted 缺失，已按 P0 派生")
    else:
        # pi 的 muted 可能与 text 差不够：迭代降亮至差 ≥0.12
        if lum(muted) >= lum(text) - 0.12:
            h, s, l = rgb_to_hsl(hex_to_rgb(muted))
            muted = shift(h, min(s, 0.44), l * 0.85)
            n = 0
            while lum(muted) >= lum(text) - 0.12 and n < 15:
                h, s, l = rgb_to_hsl(hex_to_rgb(muted))
                muted = shift(h, min(s, 0.44), l * 0.92)
                if lum(muted) < 0.02:
                    break
                n += 1
            warnings.append("colors.muted 与 text 亮度差不足，已调整")
    c["muted"] = muted
    dim = get("dim")
    if dim is None:
        dim = derive_dim(fg, muted)
        warnings.append("colors.dim 缺失，已按 P0 派生")
    else:
        # pi 的 dim 可能与 muted 差不够：迭代降亮至差 ≥0.13（留余量）
        if abs(lum(muted) - lum(dim)) < 0.10:
            h, s, l = rgb_to_hsl(hex_to_rgb(muted))
            dim = shift(h, s, l * 0.72)
            n = 0
            while abs(lum(muted) - lum(dim)) < 0.11 and n < 15:
                h, s, l = rgb_to_hsl(hex_to_rgb(dim))
                dim = shift(h, min(s, 0.44), l * 0.9)
                if lum(dim) < 0.02:
                    break
                n += 1
            warnings.append("colors.dim 与 muted 亮度差不足，已调整")
    c["dim"] = dim

    # 结构色优先从 bg 派生（pi 生态"背景分层亮度递增"规律），仅当 pi 明确
    # 提供结构色语义键（非强调色）时采用。pi 的 border 常是强调蓝，直接
    # 映射会破坏结构色纪律。
    bg_base = get("base", "mantle", "crust", "background", fallback=bg)
    umbg = get("userMessageBg", "selectedBg")
    if umbg is None:
        umbg = derive_bg_tint(bg_base, 0.80, 0.08)
        warnings.append("colors.userMessageBg/selectedBg 缺失，已派生")
    c["userMessageBg"] = umbg

    # border：先看 pi 是否提供"结构色语义"的 border（亮度介于 umbg 与 muted 之间）
    border_candidates = [get("border"), get("borderMuted")]
    border = None
    for cand in border_candidates:
        if cand is not None:
            if lum(umbg) < lum(cand) < lum(c.get("muted", "#7f849c")):
                border = cand
                break
            warnings.append(f"colors.border 是强调色（L={lum(cand):.2f}），改从 bg 派生")
    if border is None:
        border = derive_bg_tint(bg_base, 0.80, 0.16)
        warnings.append("colors.border 缺失或非结构色，已派生")
    c["border"] = border

    # line：从 bg 派生（+0.28），仅当 pi 提供满足 border<line<muted 的 line 时采用
    line_candidates = [get("borderMuted")]
    line = None
    for cand in line_candidates:
        if cand is not None and lum(border) < lum(cand) < lum(c.get("muted", "#7f849c")):
            line = cand
            break
    if line is None:
        line = derive_bg_tint(bg_base, 0.70, 0.28)
        if lum(line) >= lum(c.get("muted", "#7f849c")):
            # line 太亮：clamp 到 muted 之下
            h, s, l = rgb_to_hsl(hex_to_rgb(line))
            line = shift(h, min(s, 0.44), l * 0.92)
            while lum(line) >= lum(c.get("muted", "#7f849c")) - 0.02:
                h, s, l = rgb_to_hsl(hex_to_rgb(line))
                line = shift(h, min(s, 0.44), l * 0.94)
        warnings.append("colors.borderMuted 缺失或非结构色，已派生")
    c["line"] = line

    c["accent"] = accent
    c["brand"] = accent
    c["signal"] = accent
    c["wordmarkHighlight"] = accent
    c["wordmarkShadow"] = derive_bg_tint(bg, 1.0, -0.10)

    c["success"] = get("success") or derive_bg_tint(bg, 0.60, 0.30)
    c["warning"] = get("warning") or derive_bg_tint(bg, 0.60, 0.30)
    c["error"] = get("error") or "#FF5E6C"
    c["orbit"] = orbit

    # syntax 映射
    syn["blue"] = get("syntaxFunction", "syntaxNumber") or accent
    syn["mauve"] = get("syntaxKeyword") or accent
    syn["green"] = get("syntaxString") or c["success"]
    syn["peach"] = get("syntaxNumber") or c["warning"]
    syn["yellow"] = get("syntaxType", "mdHeading") or c["warning"]
    syn["sapphire"] = get("syntaxVariable") or get("syntaxFunction") or accent
    comment = get("syntaxComment")
    if comment is None:
        # 注释：muted 再降亮 0.80
        h, s, l = rgb_to_hsl(hex_to_rgb(c["muted"]))
        comment = shift(h, s, l * 0.80)
    syn["overlay2"] = comment
    syn["pink"] = get("syntaxOperator") or get("syntaxKeyword") or accent
    err_ref = get("toolErrorBg")
    syn["red"] = get("error") or (err_ref if err_ref else "#FF5E6C")
    syn["teal"] = get("mdCodeBlock") or c["success"]
    syn["text"] = text
    syn["subtext0"] = get("thinkingText") or c["muted"]
    syn["flamingo"] = get("syntaxPunctuation") or text

    return c, syn


# ---------- 纪律校验（与 validate-themes.py 同规格） ----------

def check_discipline(colors):
    fails = []

    def L(k):
        return lum(colors[k]) if k in colors and is_hex(colors[k]) else -1

    seq1 = ["dim", "muted", "text"]
    for a, b in zip(seq1, seq1[1:]):
        if not (L(a) < L(b)):
            fails.append(f"纪律1: 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
    seq2 = ["userMessageBg", "border", "line"]
    for a, b in zip(seq2, seq2[1:]):
        if not (L(a) < L(b)):
            fails.append(f"纪律1: 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
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
    return fails


# ---------- 主流程 ----------

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


def main(argv):
    import argparse

    ap = argparse.ArgumentParser(
        description="pi-agent 主题 → mcode 主题适配器")
    ap.add_argument("pi_theme", help="pi 主题 JSON 路径")
    ap.add_argument("--name", default=None, help="输出主题名（默认取 pi 主题 name 字段）")
    ap.add_argument("--appearance", default="dark", choices=["dark", "light"])
    ap.add_argument("--out", default=os.path.expanduser("~/.minimax/themes"),
                    help="输出目录（默认 ~/.minimax/themes）")
    args = ap.parse_args(argv)

    warnings = []

    try:
        with open(args.pi_theme, "r", encoding="utf-8") as f:
            pi = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: 无法读取 pi 主题 {args.pi_theme}: {e}", file=sys.stderr)
        return 2

    # F-06: 缺 name 或缺 colors → exit 2
    name = args.name or pi.get("name")
    if not name:
        print("error: pi 主题缺少 name（且未用 --name 指定）", file=sys.stderr)
        return 2
    if "colors" not in pi or not isinstance(pi["colors"], dict):
        print("error: pi 主题缺少 colors 键", file=sys.stderr)
        return 2

    # vars 展开（成环 → exit 3）
    try:
        pi_colors, pi_vars = resolve_vars(pi, warnings)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3

    # 映射
    colors, syn = map_theme(pi_colors, pi_vars, warnings, args.appearance)

    theme = {
        "name": name,
        "appearance": args.appearance,
        "colors": colors,
        "ansi": DEFAULT_ANSI_DARK if args.appearance == "dark" else DEFAULT_ANSI_LIGHT,
        "syntax": syn,
        "logo": colors["accent"],
    }

    # 纪律过滤（F-06）：FAIL 打印 warning 但继续
    fails = check_discipline(colors)
    for w in warnings:
        print(f"warning: {w}")
    if fails:
        print("warning: 输出主题未通过全部纪律：")
        for f_ in fails:
            print(f"    - {f_}")
    else:
        print("discipline: PASS")

    # 写出
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2, ensure_ascii=False)
    print(f"已输出: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
