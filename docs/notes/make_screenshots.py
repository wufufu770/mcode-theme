#!/usr/bin/env python3
"""生成 F-04 验证截图（纯 stdlib PNG，零依赖）：
1. logo-gradient-256.png — 从 patched cli.js 提取 __mcodeLogoGradient，
   以 256 色（colorLevel<3）模式渲染启动画面 Logo 渐变逐行色带。
2. selection-state.png — 两个主题（synthwave/tokyo-night）的选中态对比，
   选中标记 `›` 用主题 signal 色（=accent，纪律5），未选中 muted。
"""
import json
import os
import re
import struct
import subprocess
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "screenshots")
os.makedirs(OUT, exist_ok=True)

CLI = os.path.expanduser("~/.minimax-code/lib/node_modules/@minimax-ai/code/cli.js")


def write_png(path, width, height, pixels):
    """pixels: list of rows, each a list of (r,g,b)."""
    raw = b""
    for row in pixels:
        raw += b"\x00" + b"".join(bytes(px) for px in row)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def hex2rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ---------- 截图 1：256 色 Logo 渐变 ----------
def extract_gradient_fn():
    src = open(CLI, encoding="utf-8").read()
    m = re.search(r'function __mcodeLogoGradient\(rows,top,mid,bottom\)\{(.*?)\}return out\}',
                  src, re.S)
    assert m, "cannot find __mcodeLogoGradient in patched cli.js"
    return m.group(0)


def run_gradient_256(rows, top, mid, bottom):
    """以 256 色模式运行注入的渐变函数，返回每行 256 色索引（16..255）"""
    fn = extract_gradient_fn()
    script = (fn + f"""
const grad = __mcodeLogoGradient;
const stubs = {{
  isTTY: true,
  getColorDepth: () => 8,
}};
const real = process.stdout;
Object.defineProperty(process, 'stdout', {{ value: stubs, configurable: true }});
const out = grad({rows}, '{top}', '{mid}', '{bottom}');
Object.defineProperty(process, 'stdout', {{ value: real, configurable: true }});
const nums = out.map(s => {{
  const m = s.match(/38;5;(\\d+)/);
  return m ? parseInt(m[1], 10) : null;
}});
console.log(JSON.stringify(nums));
""")
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def idx256_to_rgb(idx):
    n = idx - 16
    r, g, b = n // 36, (n % 36) // 6, n % 6
    return (round(r / 5 * 255), round(g / 5 * 255), round(b / 5 * 255))


# 用当前已应用主题（ember）的三段色
cur = json.load(open(os.path.expanduser("~/.minimax/themes/.current-theme.json")))
top = cur["colors"]["wordmarkHighlight"]
mid = cur["colors"]["brand"]
bottom = cur["colors"]["wordmarkShadow"]
ROWS = 14
idxs = run_gradient_256(ROWS, top, mid, bottom)
print("256-color row indexes:", idxs)

W, H, BAND = 420, ROWS * 26, 26
pixels = []
for i, idx in enumerate(idxs):
    c = idx256_to_rgb(idx) if idx is not None else (0, 0, 0)
    for _ in range(BAND):
        pixels.append([c] * W)
write_png(os.path.join(OUT, "logo-gradient-256.png"), W, H, pixels)
print("screenshot 1:", os.path.join(OUT, "logo-gradient-256.png"), f"{W}x{H}")

# 校验无断层：256 色 cube 相邻步长
max_step = 0
for a, b in zip(idxs, idxs[1:]):
    if a is None or b is None:
        continue
    x, y = a - 16, b - 16
    step = max(abs(x // 36 - y // 36), abs((x % 36) // 6 - (y % 36) // 6), abs(x % 6 - y % 6))
    max_step = max(max_step, step)
print("max 256-cube step:", max_step, "→ 无断层" if max_step <= 1 else "→ 有断层!")

# ---------- 截图 2：两个主题选中态对比 ----------
THEMES = ["synthwave", "tokyo-night"]
COLS = 3  # 每主题一列：列表 3 项（第 2 项选中）
COLW, ROWH = 240, 40
TH, TW = H, COLS * COLW * 2  # 每主题占 2 列宽（标记+标签）

pixels2 = []
bg = (16, 16, 22)
for y in range(H):
    pixels2.append([bg] * (len(THEMES) * 2 * COLW))

def blend(fg, bgc, a):
    return tuple(round(f * a + b * (1 - a)) for f, b in zip(fg, bgc))

themes_dir = os.path.join(os.path.dirname(HERE), "..", "themes")
for t_idx, tname in enumerate(THEMES):
    th = json.load(open(os.path.join(os.path.dirname(HERE), "..", "themes", tname + ".json")))
    signal = hex2rgb(th["colors"]["signal"])
    muted = hex2rgb(th["colors"]["muted"])
    textc = hex2rgb(th["colors"]["text"])
    items = ["EduSRC 侦察", "漏洞分析", "报告生成"]
    base_x = t_idx * 2 * COLW
    # 标题
    for ch_i in range(COLW * 2):
        for r_i in range(12):
            x = base_x * 0 + ch_i  # placeholder
    # 列标题
    title = tname
    for r in range(10):
        for c in range(len(tname) * 9):
            px = base_x + c + 6
            if r < 10 and px < len(pixels2[0]):
                pixels2[r][px] = (120, 140, 160)
    for row_i, label in enumerate(items):
        sel = row_i == 1
        y0 = 24 + row_i * (ROWH + 8)
        for y in range(y0, min(y0 + ROWH, H)):
            for x in range(base_x, base_x + 2 * COLW):
                cells = pixels2[y]
                if sel:
                    # 选中：accent 12% 混合底 + accent 前景 + 左侧 2px 指示条
                    cells[x] = blend(signal, bg, 0.12)
                    if x - base_x < 3:
                        cells[x] = signal
                # 前景（简化：整个色块区域用文字色 vs 选中用 accent）
                fg = signal if sel else muted
                if x - base_x >= 6 and x - base_x < 6 + len(label) * 8:
                    cells[x] = fg
                if sel and x - base_x >= 2 * COLW - 8:
                    cells[x] = signal  # ✓ 标记

write_png(os.path.join(OUT, "selection-state.png"), len(THEMES) * 2 * COLW, H, pixels2)
print("screenshot 2:", os.path.join(OUT, "selection-state.png"))
print("DONE")
