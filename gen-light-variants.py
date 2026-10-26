#!/usr/bin/env python3
"""gen-light-variants.py — 从 dark 主题派生 light 变体。

mcode 0.7.0 原生按主题 JSON 的 name 字段分组：同名 + 不同 appearance 的两个
文件会被合并成同一个主题条目，选择器里可用 ←/→ 切外观。仓库里只有 dark 版，
于是切到 light 时会回落到 mcode 内置 minimax 浅色调色板（不是这个主题的浅色）。

本脚本按角色做色相/饱和度保持的明度重映射，为每个 dark 主题生成配套 light 变体：
  背景类  userMessageBg / diffAddedBg / diffRemovedBg → 极浅色调
  前景类  text → 深色     muted / dim → 中间调
  描边类  border / line → 浅描边
  强调类  brand / accent / signal / orbit / markdown* / success / warning / error
          → 保持色相与饱和度，明度压到浅底可读的区间

用法：
    python3 gen-light-variants.py [themes目录]      # 默认 ./themes
    python3 gen-light-variants.py --check [目录]     # 只检查不写
"""
import colorsys
import json
import os
import sys

# 语义角色 → 明度处理策略
BG_ROLES = {"userMessageBg", "diffAddedBg", "diffRemovedBg"}
FG_ROLES = {"text"}
MUTED_ROLES = {"muted", "dim"}
LINE_ROLES = {"border", "line"}
# 其余（强调色）走 ACCENT 处理

SYNTAX_LIGHT = {
    # 语法高亮的浅色映射基准（相对暗色主题做明度上移）
    "lift": 0.22,
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def rgb_to_hsl(rgb):
    r, g, b = (v / 255.0 for v in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60, s, l


def hsl_to_rgb(h, s, l):
    h = h % 360
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        rgb = (c, x, 0)
    elif h < 120:
        rgb = (x, c, 0)
    elif h < 180:
        rgb = (0, c, x)
    elif h < 240:
        rgb = (0, x, c)
    elif h < 300:
        rgb = (x, 0, c)
    else:
        rgb = (c, 0, x)
    return tuple((v + m) * 255 for v in rgb)


def shift(hexcolor, dl=0.0, ds=0.0, hue=0.0, lmin=None, lmax=None):
    """色相/饱和度/明度微调。lmin/lmax 给出后做钳制。"""
    h, s, l = rgb_to_hsl(hex_to_rgb(hexcolor))
    h = (h + hue) % 360
    s = max(0.0, min(1.0, s + ds))
    l = max(0.0, min(1.0, l + dl))
    if lmin is not None:
        l = max(lmin, l)
    if lmax is not None:
        l = min(lmax, l)
    return rgb_to_hex(hsl_to_rgb(h, s, l))


def remap(hexcolor, target_l, target_s=None, lmin=None, lmax=None):
    """保留原色相，把明度换成角色目标值（可选同时收敛饱和度）。

    角色目标明度是「语义」而非「原值映射」——这样每个主题的浅色版都符合
    可读性约定，同时用原色相保留了主题个性（不会 22 个主题的浅色版长得一样）。
    """
    h, s, _ = rgb_to_hsl(hex_to_rgb(hexcolor))
    l = target_l
    if target_s is not None:
        s = target_s
    if lmin is not None:
        l = max(lmin, l)
    if lmax is not None:
        l = min(lmax, l)
    return rgb_to_hex(hsl_to_rgb(h, s, l))


def scale_l(hexcolor, base, gain, lmin=None, lmax=None):
    """明度做单调线性映射（保持原有相对顺序，不会把不同颜色压成同一个值）。"""
    h, s, l = rgb_to_hsl(hex_to_rgb(hexcolor))
    l = base + l * gain
    if lmin is not None:
        l = max(lmin, l)
    if lmax is not None:
        l = min(lmax, l)
    return rgb_to_hex(hsl_to_rgb(h, s, l))


def _luminance(hexcolor):
    def ch(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in hex_to_rgb(hexcolor))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def ensure_contrast(hexcolor, bg, min_ratio=3.0):
    """保证颜色对背景的对比度达标：不够就沿明度轴压暗（保持色相/饱和度）。"""
    if contrast_ratio(hexcolor, bg) >= min_ratio:
        return hexcolor
    h, s, l = rgb_to_hsl(hex_to_rgb(hexcolor))
    for i in range(60):
        l = max(0.0, l - 0.02)
        cand = rgb_to_hex(hsl_to_rgb(h, s, l))
        if contrast_ratio(cand, bg) >= min_ratio:
            return cand
    return rgb_to_hex(hsl_to_rgb(h, s, 0.12))


def derive_light_theme(theme):
    """把一个 dark 主题派生成 light 变体。

    中性色（text/muted/dim/border/line）用「角色目标明度 + 原色相」：
      浅底上 text 必须最深、muted 次之、dim 更浅、border 最淡、line 是分隔线。
      原色相保留 → 每个主题的浅色版仍有自己的味道。
    强调色用单调线性明度映射 → 保持 brand / wordmarkHighlight 之间的对比关系。
    """
    colors = theme.get("colors") or {}
    syntax = theme.get("syntax") or {}
    out_colors = {}

    for k, v in colors.items():
        if not isinstance(v, str) or not v.startswith("#"):
            out_colors[k] = v
            continue
        if k == "userMessageBg":
            h, s, _ = rgb_to_hsl(hex_to_rgb(v))
            out_colors[k] = rgb_to_hex(hsl_to_rgb(h, min(s, 0.30), 0.962))
        elif k in BG_ROLES:
            h, s, _ = rgb_to_hsl(hex_to_rgb(v))
            out_colors[k] = rgb_to_hex(hsl_to_rgb(h, min(s, 0.32), 0.935))
        elif k == "text":
            out_colors[k] = remap(v, 0.235, 0.16)
        elif k == "muted":
            out_colors[k] = remap(v, 0.455, 0.14)
        elif k == "dim":
            out_colors[k] = remap(v, 0.605, 0.12)
        elif k == "border":
            out_colors[k] = remap(v, 0.795, 0.13)
        elif k == "line":
            out_colors[k] = remap(v, 0.875, 0.12)
        else:
            # 强调色：单调映射，明度压到浅底可读区间
            out_colors[k] = scale_l(v, 0.245, 0.300, lmin=0.26, lmax=0.575)

    # 对比度兜底：强调色在浅底上至少 3:1
    bg = out_colors.get("userMessageBg", "#F5F5F7")
    for k, v in list(out_colors.items()):
        if k in BG_ROLES or k in FG_ROLES or k in MUTED_ROLES or k in LINE_ROLES:
            continue
        out_colors[k] = ensure_contrast(v, bg, 3.0)

    out_syntax = {}
    for k, v in syntax.items():
        if not isinstance(v, str) or not v.startswith("#"):
            out_syntax[k] = v
            continue
        out_syntax[k] = scale_l(v, 0.245, 0.335, lmin=0.245, lmax=0.585)

    out = {
        "name": theme["name"],
        "appearance": "light",
        "colors": out_colors,
        "syntax": out_syntax,
    }
    if theme.get("label"):
        out["label"] = theme["label"]
    if theme.get("description"):
        out["description"] = theme["description"]
    # ansi 降级色沿用（浅色下 ANSI 名不变）
    if theme.get("ansi"):
        out["ansi"] = theme["ansi"]
    if theme.get("vars"):
        out["vars"] = theme["vars"]
    return out


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    check = "--check" in argv
    d = args[0] if args else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "themes")
    if not os.path.isdir(d):
        print("no such directory: %s" % d, file=sys.stderr)
        return 2

    made = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn.startswith("."):
            continue
        src = os.path.join(d, fn)
        try:
            with open(src, "r", encoding="utf-8") as f:
                theme = json.load(f)
        except (OSError, ValueError):
            continue
        if theme.get("appearance") != "dark":
            continue
        light = derive_light_theme(theme)
        dest = os.path.join(d, "%s.light.json" % theme["name"])
        made.append((theme["name"], dest, light))

    for name, dest, light in made:
        if check:
            print("would write %s" % dest)
            continue
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(light, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("wrote %s" % dest)
    print("\n共 %d 个 light 变体%s" % (len(made), "（--check，未写入）" if check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
