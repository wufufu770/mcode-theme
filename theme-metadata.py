#!/usr/bin/env python3
"""theme-metadata.py — 为主题库补 label / description（mcode /theme 选择器会显示）。

mcode 0.7.0 的主题选择器渲染三样东西：
  - label      → 列表里显示的名字（≤40 字符）
  - description→ 详情区的 "About" 行（≤120 字符）
  - source     → "custom file"（自定义）/ "built-in"（内置）

description 用主题自身的配色特征自动生成（取品牌色/背景色/强调色的色相描述），
label 用可读化后的名字。

用法：
    python3 theme-metadata.py [themes目录]   # 默认 ./themes
    python3 theme-metadata.py --check [目录]
"""
import colorsys
import json
import os
import re
import sys


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hue_of(hexcolor):
    r, g, b = (v / 255.0 for v in hex_to_rgb(hexcolor))
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0.0
    d = mx - mn
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60


def hue_name(h):
    if h < 15 or h >= 345:
        return "red"
    if h < 40:
        return "orange"
    if h < 70:
        return "amber"
    if h < 95:
        return "yellow"
    if h < 150:
        return "green"
    if h < 185:
        return "teal"
    if h < 210:
        return "cyan"
    if h < 250:
        return "blue"
    if h < 280:
        return "violet"
    if h < 320:
        return "magenta"
    return "pink"


PRETTY = {
    "catppuccin-mocha": ("Catppuccin Mocha", "Pastel-toned Latte palette — soft lilac and rose accents"),
    "cyberpunk": ("Cyberpunk", "Neon magenta and cyan on deep black — high-energy synthwave"),
    "deepseek": ("DeepSeek", "Cool indigo and slate — calm, low-glare editor palette"),
    "dracula": ("Dracula", "Classic purple and pink — the original dark pastel theme"),
    "ember": ("Ember", "Warm amber and rust on charcoal — low-blue night palette"),
    "emerald": ("Emerald", "Deep green and jade on near-black — forest-floor greens"),
    "everforest-dark": ("Everforest Dark", "Muted olive and sage — low-contrast, easy on the eyes"),
    "github-dark": ("GitHub Dark", "GitHub's own dark theme — familiar blue-gray neutrals"),
    "gruvbox-dark": ("Gruvbox Dark", "Retro warm earth tones with a paper-like background"),
    "material-palenight": ("Material Palenight", "Material Design's deep indigo night variant"),
    "minimax-light": ("MiniMax Light", "The official MiniMax light palette — clean and airy"),
    "minimax-official": ("MiniMax Official", "The official MiniMax blue palette, tuned for truecolor"),
    "monokai": ("Monokai", "The classic olive-and-purple code palette"),
    "monokai-pro": ("Monokai Pro", "Monokai with extra syntax roles — richer highlighting"),
    "nord": ("Nord", "Arctic blue-gray — famously restrained and calm"),
    "one-dark": ("One Dark", "Atom's dark theme — balanced blue-gray with amber accents"),
    "rose-pine": ("Rosé Pine", "Soft rose, pine and gold — a warm take on Allura"),
    "solarized-dark": ("Solarized Dark", "Solarized's dark variant — precise, low-strain contrast"),
    "synthwave": ("Synthwave", "Hot magenta and cyan with a purple horizon glow"),
    "tokyo-night": ("Tokyo Night", "Neon Tokyo at night — indigo base with vivid accents"),
    "vesper": ("Vesper", "Deep charcoal with warm amber — restrained and premium"),
    "violet": ("Violet", "Rich violet and plum on near-black"),
}


def auto_description(theme):
    """没有预置文案时，按调色板特征生成一句描述。"""
    c = theme.get("colors") or {}
    brand = c.get("brand") or "#888888"
    h = hue_of(brand)
    bg = c.get("userMessageBg") or "#000000"
    bl = sum(hex_to_rgb(bg)) / 3 / 255
    tone = "light" if bl > 0.55 else ("mid-tone" if bl > 0.28 else "deep")
    hn = hue_name(h)
    return "%s %s palette with %s accents" % (tone, hn, hn)


def pretty_label(name):
    if name in PRETTY:
        return PRETTY[name][0]
    words = re.split(r"[-_]+", name)
    return " ".join(w.capitalize() for w in words)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    check = "--check" in argv
    d = args[0] if args else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "themes")
    if not os.path.isdir(d):
        print("no such directory: %s" % d, file=sys.stderr)
        return 2

    n = 0
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn.startswith("."):
            continue
        path = os.path.join(d, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                theme = json.load(f)
        except (OSError, ValueError):
            continue
        name = theme.get("name")
        if not name:
            continue
        label, desc = PRETTY.get(name, (None, None))
        label = label or pretty_label(name)
        desc = desc or auto_description(theme)
        if theme.get("label") == label and theme.get("description") == desc:
            continue
        if check:
            print("would update %s -> label=%r" % (fn, label))
            continue
        # 保持字段顺序：name, appearance, label, description, colors, ...
        new = {}
        for k in ("name", "appearance"):
            if k in theme:
                new[k] = theme[k]
        new["label"] = label
        new["description"] = desc
        for k, v in theme.items():
            if k not in new:
                new[k] = v
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("updated %s: label=%r" % (fn, label))
        n += 1
    print("\n共更新 %d 个主题%s" % (n, "（--check，未写入）" if check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
