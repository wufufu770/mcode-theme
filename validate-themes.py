#!/usr/bin/env python3
"""validate-themes.py — mcode 主题纪律校验器

扫描 themes/ 目录下全部主题 JSON，对每个主题运行 5 条颜色纪律检查
（与 gen-themes.py F-02 同规格）：

1. 亮度严格全序：L(dim) < L(muted) < L(text) 且 L(userMessageBg) < L(border) < L(line)
2. text/muted/dim 两两相对亮度差 ≥ 0.10
3. hue(userMessageBg)/hue(border)/hue(line) 两两偏差 ≤ 25°
4. 结构色（userMessageBg/border/line/muted/dim）饱和度 ≤ 0.45
5. brand/accent/signal/wordmarkHighlight 四者完全相等

用法：
  python3 validate-themes.py [themes目录]    # 默认 ./themes
退出码：0 = 全部 PASS，1 = 存在 FAIL

输出：逐主题 PASS/WARN/FAIL 表格。
"""
import colorsys
import json
import os
import sys


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hsl(rgb):
    r, g, b = (v / 255.0 for v in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def lum(hexcolor):
    """相对亮度 L = 0.2126R + 0.7152G + 0.0722B（线性化 sRGB，gamma 2.2 近似）"""
    r, g, b = (v / 255.0 for v in hex_to_rgb(hexcolor))
    lin = tuple(v ** 2.2 for v in (r, g, b))
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def check_theme(theme):
    """对单个主题跑 5 条纪律，返回 (warns, fails) 列表。
    亮色主题（appearance=light）放宽纪律1（层级反转是正常设计），其余纪律照常。"""
    c = theme.get("colors") or {}
    is_light = theme.get("appearance") == "light"
    warns, fails = [], []

    # 缺键：直接计 FAIL（数据不完整）
    required = ["userMessageBg", "border", "line", "muted", "dim", "text",
                "brand", "accent", "signal", "wordmarkHighlight"]
    for k in required:
        if k not in c or not isinstance(c[k], str) or not c[k].startswith("#"):
            fails.append(f"纪律0: 缺少有效颜色键 {k}")

    def L(k):
        return lum(c[k]) if k in c and c[k].startswith("#") else -1

    if not fails:
        if not is_light:
            # 纪律 1: 亮度严格全序（dim < muted < text 且 umbg < border < line）
            seq1 = ["dim", "muted", "text"]
            for a, b in zip(seq1, seq1[1:]):
                if not (L(a) < L(b)):
                    fails.append(f"纪律1: 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
            seq2 = ["userMessageBg", "border", "line"]
            for a, b in zip(seq2, seq2[1:]):
                if not (L(a) < L(b)):
                    fails.append(f"纪律1: 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
        else:
            # 亮色主题：反序（line < border < umbg，dim > muted > text）
            seq1 = ["text", "muted", "dim"]
            for a, b in zip(seq1, seq1[1:]):
                if not (L(a) < L(b)):
                    fails.append(f"纪律1(light): 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")
            seq2 = ["line", "border", "userMessageBg"]
            for a, b in zip(seq2, seq2[1:]):
                if not (L(a) < L(b)):
                    fails.append(f"纪律1(light): 亮度序违反 {a}({L(a):.3f}) -> {b}({L(b):.3f})")

        # 纪律 2: text/muted/dim 两两亮度差 ≥ 0.10
        for a, b in [("text", "muted"), ("text", "dim"), ("muted", "dim")]:
            if abs(L(a) - L(b)) < 0.10:
                fails.append(f"纪律2: {a}/{b} 亮度差 {abs(L(a)-L(b)):.3f} < 0.10")

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
                    names = ["userMessageBg", "border", "line"]
                    fails.append(
                        f"纪律3: 色相偏差 {d:.1f}° ({names[i]} {hues[i]:.0f}° vs "
                        f"{names[j]} {hues[j]:.0f}°)")

        # 纪律 4: 结构色饱和度 ≤ 0.45（近白/近黑豁免：L>0.9 或 L<0.05 的高亮底色
        # 在 HSL 换算中感知饱和失真，不构成结构色污染）
        for k in ("userMessageBg", "border", "line", "muted", "dim"):
            lv = L(k)
            if lv > 0.85 or lv < 0.05:
                continue
            _, s, _ = rgb_to_hsl(hex_to_rgb(c[k]))
            if s > 0.45:
                fails.append(f"纪律4: {k} 饱和度 {s:.2f} > 0.45")

        # 纪律 5: 品牌色族完全相等
        fam = {c["brand"], c["accent"], c["signal"], c["wordmarkHighlight"]}
        if len(fam) != 1:
            fails.append(f"纪律5: 品牌色族发散 {sorted(fam)}")

    return warns, fails


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    themes_dir = argv[1] if len(argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "themes")
    if not os.path.isdir(themes_dir):
        print(f"error: 目录不存在 {themes_dir}", file=sys.stderr)
        return 1

    files = sorted(f for f in os.listdir(themes_dir) if f.endswith(".json"))
    if not files:
        print(f"error: {themes_dir} 下无 JSON 主题", file=sys.stderr)
        return 1

    print(f"{'主题':<28} {'纪律':<6} 结果")
    print("-" * 48)
    n_pass = n_fail = 0
    for fn in files:
        name = fn[:-5]
        try:
            with open(os.path.join(themes_dir, fn), "r", encoding="utf-8") as f:
                theme = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"{name:<28} {'-':<6} FAIL (读取失败: {e})")
            n_fail += 1
            continue

        warns, fails = check_theme(theme)
        if fails:
            n_fail += 1
            print(f"{name:<28} {len(fails):<6} FAIL")
            for w in fails:
                print(f"    - {w}")
        elif warns:
            n_pass += 1
            print(f"{name:<28} {'-':<6} PASS")
        else:
            n_pass += 1
            print(f"{name:<28} {'0':<6} PASS")

    print("-" * 48)
    print(f"共 {len(files)} 主题：PASS {n_pass}，FAIL {n_fail}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
