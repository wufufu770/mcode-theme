#!/usr/bin/env python3
"""mcode_theme_lib - mcode-theme 核心逻辑"""
#!/usr/bin/env python3
"""
mcode-theme - MiniMax Code CLI 主题安装工具（完整版）

用法:
  mcode-theme install <theme.json>      安装主题到 mcode（打补丁）
  mcode-theme apply <name>              应用已安装的主题
  mcode-theme list                      列出已安装主题
  mcode-theme restore                   恢复官方默认主题
  mcode-theme current                   显示当前主题
  mcode-theme create <name>             生成主题模板（基于官方 dark 主题）

原理:
  mcode 的 cli.js 是单文件 bundle，包含 6 个主题定义点：
  1. Ket  = UI 主题 dark   (hex)
  2. Yet  = UI 主题 light  (hex)
  3. AHo.dark  = ANSI 8 色回退主题 dark  (colorLevel=1 时用)
  4. AHo.light = ANSI 8 色回退主题 light
  5. Sri.dark  = 代码语法高亮主题 dark  (Catppuccin 风格)
  6. Sri.light = 代码语法高亮主题 light
  本工具一次性替换全部 6 处。

主题 JSON 格式:
  {
    "name": "my-theme",
    "appearance": "dark",
    "colors": { ...15 个 UI 键... },
    "ansi": { ...可选，15 个 ANSI 命名色键... },
    "syntax": { ...可选，14 个语法高亮键... }
  }
"""

import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time

IS_WINDOWS = os.name == "nt" or sys.platform.startswith("win")


def _mcode_install_root():
    """mcode 安装根目录（与 cli.js Elr() 逻辑一致）：
    Windows: %LOCALAPPDATA%/MinimaxCode（或 MCODE_INSTALL_ROOT）
    macOS/Linux: ~/.local/share/minimax-code（或 MCODE_INSTALL_ROOT）"""
    override = os.environ.get("MCODE_INSTALL_ROOT")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise RuntimeError("LOCALAPPDATA is required to resolve the MCode install root.")
        return os.path.join(local, "MinimaxCode")
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return os.path.join(os.path.abspath(os.path.expanduser(xdg)), "minimax-code")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "minimax-code")


def _candidate_install_roots():
    """所有可能的安装根（按优先级）：显式覆盖 > 平台默认 > 历史 npm-prefix 路径。
    返回含 cli.js 的实际路径优先，保证旧安装（~/.minimax-code）也能工作。"""
    roots = []
    override = os.environ.get("MCODE_INSTALL_ROOT")
    if override:
        roots.append(os.path.abspath(os.path.expanduser(override)))
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            roots.append(os.path.join(local, "MinimaxCode"))
    else:
        roots.append(os.path.expanduser("~/.minimax-code"))  # 历史 npm --prefix 安装
        # npm 默认全局安装路径（~/.npm-global/lib/node_modules）
        npm_global_prefix = os.path.join(os.path.expanduser("~"), ".npm-global")
        if os.path.isdir(os.path.join(npm_global_prefix, "lib", "node_modules")):
            roots.append(npm_global_prefix)
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            roots.append(os.path.join(os.path.abspath(os.path.expanduser(xdg)), "minimax-code"))
        roots.append(os.path.join(os.path.expanduser("~"), ".local", "share", "minimax-code"))
    return roots


def _mcode_lib_dir():
    """定位实际存在的 mcode lib 目录（含 cli.js 的优先）：
    1. 优先使用 which mcode 解析出的真实路径（跟随符号链接）
    2. 回退到候选安装根列表"""
    import shutil
    mcode_bin = shutil.which("mcode")
    if mcode_bin:
        real_path = os.path.realpath(mcode_bin)
        # real_path 是 cli.js 的真实路径，直接返回其所在目录
        candidate = os.path.dirname(real_path)
        if os.path.isfile(os.path.join(candidate, "cli.js")):
            return candidate
    for root in _candidate_install_roots():
        candidate = os.path.join(root, "lib", "node_modules", "@minimax-ai", "code")
        if os.path.isfile(os.path.join(candidate, "cli.js")):
            return candidate
    return os.path.join(_candidate_install_roots()[0], "lib", "node_modules", "@minimax-ai", "code")


def _mcode_data_dir():
    """mcode 数据目录：~/.minimax（所有平台统一）"""
    return os.path.join(os.path.expanduser("~"), ".minimax")


def _node_executable_name():
    """node 可执行文件名（Windows 为 node.exe）"""
    return "node.exe" if IS_WINDOWS else "node"


MCODE_LIB = _mcode_lib_dir()
CLI_PATH = os.path.join(MCODE_LIB, "cli.js")
BACKUP_PATH = os.path.join(MCODE_LIB, "cli.js.minimax-original")
MCODE_DATA_DIR = _mcode_data_dir()
TUI_DIR = os.path.join(MCODE_DATA_DIR, "tui")
# 原生主题目录：mcode 会扫描该目录下全部 *.json（schema 严格校验）
THEME_DIR = os.path.join(TUI_DIR, "themes")
# mcode 记录当前选中主题的设置文件
SETTINGS_FILE = os.path.join(TUI_DIR, "tui-settings.json")
# 本工具的元数据目录（放在 themes/ 之外，避免被 mcode 当主题扫描）
STATE_DIR = os.path.join(MCODE_DATA_DIR, "mcode-theme")
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_lib_dir():
    """主题库目录（mcode-theme 自有格式，供 Web 配置器编辑）。

    优先级：
      1) ~/.local/share/mcode-themes          （install.sh 安装位置）
      2) <repo>/themes                        （直接从源码仓库运行）
      3) ~/.local/share/mcode-themes          （兜底）
    """
    candidates = [
        os.path.join(os.path.dirname(TOOL_DIR), "share", "mcode-themes"),
        os.path.join(os.path.dirname(TOOL_DIR), "mcode-themes", "themes"),
        os.path.join(os.path.expanduser("~"), ".local", "share", "mcode-themes"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[-1]


LIB_DIR = _resolve_lib_dir()
CURRENT_FILE = os.path.join(STATE_DIR, "current-theme.json")
LAST_APPLIED_FILE = os.path.join(STATE_DIR, "last-applied.json")

UI_KEYS = [
    "brand", "wordmarkHighlight", "wordmarkShadow", "signal", "orbit",
    "accent", "markdownHeading", "markdownCode", "markdownLink",
    "userMessageBg", "diffAddedBg", "diffRemovedBg",
    "text", "muted", "dim", "border", "line",
    "success", "warning", "error",
]

# mcode >= 0.7.0 原生 schema 允许的键（与 UI_KEYS 同序）
NATIVE_UI_KEYS = list(UI_KEYS)
# mcode >= 0.7.0 新增的 5 个 UI 键（旧主题没有，需从调色板派生）
NATIVE_NEW_UI_KEYS = ["markdownHeading", "markdownCode", "markdownLink",
                      "diffAddedBg", "diffRemovedBg"]
NATIVE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$", re.I)
# mcode 内置主题 id：同名自定义文件会被 mcode 忽略
BUILTIN_THEME_IDS = ["minimax", "midnight", "graphite", "aurora"]

SYNTAX_KEYS = [
    "blue", "flamingo", "green", "mauve", "overlay2", "peach", "pink",
    "red", "sapphire", "subtext0", "teal", "text", "yellow",
]

DEFAULT_UI = {
    "dark": {
        "brand": "#68C0FF", "wordmarkHighlight": "#93D2FF", "wordmarkShadow": "#3DAEFF",
        "signal": "#68C0FF", "orbit": "#1CCDD2", "accent": "#68C0FF",
        "markdownHeading": "#CBA6F7", "markdownCode": "#A6E3A1",
        "markdownLink": "#68C0FF",
        "userMessageBg": "#262626", "diffAddedBg": "#213A2B",
        "diffRemovedBg": "#4A221D",
        "text": "#EDEDED", "muted": "#ADADAD",
        "dim": "#666666", "border": "#303030", "line": "#666666",
        "success": "#28C567", "warning": "#FFC340", "error": "#FF5E6C",
    },
    "light": {
        "brand": "#0094FC", "wordmarkHighlight": "#3DAEFF", "wordmarkShadow": "#0077D9",
        "signal": "#0094FC", "orbit": "#00767D", "accent": "#0094FC",
        "markdownHeading": "#8839EF", "markdownCode": "#267A3F",
        "markdownLink": "#0066CC",
        "userMessageBg": "#F5F5F5", "diffAddedBg": "#DAFBE1",
        "diffRemovedBg": "#FFEBE9",
        "text": "#303030", "muted": "#666666",
        "dim": "#949494", "border": "#EDEDED", "line": "#949494",
        "success": "#008635", "warning": "#916300", "error": "#E31937",
    },
}

DEFAULT_ANSI = {
    "dark": {
        "brand": "cyanBright", "wordmarkHighlight": "whiteBright", "wordmarkShadow": "cyan",
        "signal": "cyanBright", "orbit": "cyan", "accent": "cyanBright",
        "text": "whiteBright", "muted": "white", "dim": "gray",
        "border": "gray", "line": "gray", "success": "greenBright",
        "warning": "yellowBright", "error": "redBright",
    },
    "light": {
        "brand": "blueBright", "wordmarkHighlight": "blueBright", "wordmarkShadow": "blue",
        "signal": "blueBright", "orbit": "cyan", "accent": "blueBright",
        "text": "black", "muted": "black", "dim": "gray",
        "border": "gray", "line": "gray", "success": "green",
        "warning": "yellow", "error": "red",
    },
}

DEFAULT_SYNTAX = {
    "dark": {
        "blue": "#89B4FA", "flamingo": "#F2CDCD", "green": "#A6E3A1",
        "mauve": "#CBA6F7", "overlay2": "#9399B2", "peach": "#FAB387",
        "pink": "#F5C2E7", "red": "#F38BA8", "sapphire": "#74C7EC",
        "subtext0": "#A6ADC8", "teal": "#94E2D5", "text": "#CDD6F4",
        "yellow": "#F9E2AF",
    },
    "light": {
        "blue": "#1E66F5", "flamingo": "#DD7878", "green": "#40A02B",
        "mauve": "#8839EF", "overlay2": "#7C7F93", "peach": "#FE640B",
        "pink": "#EA76CB", "red": "#D20F39", "sapphire": "#209FB5",
        "subtext0": "#6C6F85", "teal": "#179299", "text": "#4C4F69",
        "yellow": "#DF8E1D",
    },
}

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ANSI_RE = re.compile(r"^(black|red|green|yellow|blue|magenta|cyan|white|gray|blackBright|redBright|greenBright|yellowBright|blueBright|magentaBright|cyanBright|whiteBright)$")


def err(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ============ 安全防护（路径穿越 / SSRF 整改） ============

def sanitize_path(path, root):
    """路径清洗（防路径穿越）：realpath(path) 必须等于 root 或位于其下，否则拒绝。
    同时封死符号链接逃逸与 '..' 穿越（realpath 已解析两者）。
    调用方必须以赋值形式接收返回值以重建数据流：path = sanitize_path(path, root)。"""
    root_real = os.path.realpath(root)
    real = os.path.realpath(path)
    if real != root_real and not real.startswith(root_real + os.sep):
        raise ValueError("拒绝访问允许目录之外的路径: %s" % path)
    return real


# 兼容旧名
checked_write_path = sanitize_path


def safe_write_open(path, root, mode="w", **kw):
    """经 sanitize_path 校验的写句柄封装（全部写盘的统一卡口）。
    内部走 pathlib 的 open（非内置 open），校验语义不变。"""
    path = sanitize_path(path, root)   # 清洗并赋值重建数据流
    return pathlib.Path(path).open(mode, **kw)


def safe_read_open(path, root, mode="r", **kw):
    """经 sanitize_path 校验的读句柄封装（读侧统一卡口，防目录逃逸）。"""
    path = sanitize_path(path, root)   # 清洗并赋值重建数据流
    return pathlib.Path(path).open(mode, **kw)


def sanitize_theme_name(name):
    """主题名校验：写入 THEME_DIR 前拒绝路径分隔符/穿越/控制字符。"""
    name = (name or "").strip()
    if not name or len(name) > 100:
        err("theme name invalid (empty or too long)")
    if re.search(r'[\\/\x00-\x1f:*?"<>|]', name) or name.startswith(".") or ".." in name:
        err("theme name must not contain path separators, '..' or control chars: %r" % name)
    return name


def validate_fetch_url(url):
    """install 远程来源 URL 校验（防 SSRF）：仅 http/https；
    DNS 解析后拒绝环回/私网/链路本地/保留/组播/未指定地址。"""
    import ipaddress
    import socket
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        err("仅支持 http/https 主题来源: %s" % url)
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except OSError as e:
        err("无法解析主机 %s: %s" % (p.hostname, e))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            err("拒绝访问内网/保留地址（SSRF 防护）: %s → %s" % (p.hostname, ip))
    return url


def safe_urlopen(url, timeout=30):
    """经 validate_fetch_url 校验的 urlopen 封装（SSRF 统一卡口），
    校验后以返回值赋值重建数据流。"""
    import urllib.request
    url = validate_fetch_url(url)
    return urllib.request.urlopen(url, timeout=timeout)


# ============ 补丁安全 ============

# TUI 冒烟崩溃关键词（node 崩溃栈特征）
SMOKE_CRASH_KEYWORDS = (
    "is not defined",
    "stopped unexpectedly",
    "ReferenceError",
    "TypeError:",
    "SyntaxError",
    "RangeError:",
    "uncaught",
    "Segmentation fault",
    "heap out of memory",
)


def _mcode_bin_candidates():
    """mcode 可执行候选：PATH > 安装根 bin/ > npm 全局 bin。"""
    cands = []
    w = shutil.which("mcode")
    if w:
        cands.append(w)
    cands.append(os.path.normpath(os.path.join(MCODE_LIB, "..", "..", "..", "..", "bin", "mcode")))
    if IS_WINDOWS:
        cands.append(os.path.normpath(os.path.join(MCODE_LIB, "..", "..", "..", "..", "bin", "mcode.cmd")))
    return cands


def run_tui_smoke(seconds=40, min_render_bytes=1500):
    """TUI 启动冒烟验证 v2（真实渲染路径）：

    v1（`timeout 8 mcode </dev/null`）存在致命盲区——mcode 冷启动需 ~20s，
    且非 TTY 模式下 TUI 渲染路径根本不执行（输出 "requires a TTY" 即退出），
    渲染期崩溃（如渐变插桩的 ReferenceError）完全检测不到。

    v2：用标准库 pty 在真实终端下启动 mcode，等待渲染首帧：
      - 出现渲染帧（≥min_render_bytes 字节，默认 1500）且无崩溃关键词 → PASS（提前返回）
      - 输出含崩溃关键词（is not defined / stopped unexpectedly / ReferenceError…）→ FAIL
      - 超时仍无渲染帧 → FAIL（TUI 未能启动渲染，宁可拒绝也不交付可能崩溃的 patch）
      - 信号终止/执行失败 → FAIL
    返回 (ok: bool, head: str 前 5 行输出)。

    测试钩子：MCODE_THEME_SMOKE_MOCK=fail|pass 可强制结果（仅用于验收测试，
    生产路径始终执行真实 pty 渲染冒烟，不得跳过）。"""
    mock = os.environ.get("MCODE_THEME_SMOKE_MOCK")
    if mock == "fail":
        return False, "[mock] ReferenceError: broken is not defined"
    if mock == "pass":
        return True, "[mock] TUI frame rendered"
    smoke_mode = os.environ.get("MCODE_THEME_SMOKE")
    if smoke_mode == "0":
        # 快速模式：跳过冒烟（仅 node --check 辅助校验）
        return True, "[skip] MCODE_THEME_SMOKE=0"

    if IS_WINDOWS or smoke_mode == "fast":
        # Windows 无 pty / fast 模式：管道检测（模块加载期崩溃可捕获，~9s；
        # 渲染期崩溃需真实 pty，完整模式才覆盖）
        mcode_bin = next((c for c in _mcode_bin_candidates()
                          if c and os.path.isfile(c)), None)
        if not mcode_bin:
            return False, "未找到 mcode 可执行文件（PATH 与安装目录均无）"
        try:
            r = subprocess.run(["timeout", "8", mcode_bin],
                               stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=12)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, f"冒烟执行失败: {e}"
        out = (r.stdout or "") + (r.stderr or "")
        head = "\n".join((out.splitlines() or [""])[:5])
        if r.returncode == 124:
            return True, head
        if r.returncode < 0:
            return False, head
        if any(k in out for k in SMOKE_CRASH_KEYWORDS):
            return False, head
        return True, head

    import pty
    import select
    mcode_bin = next((c for c in _mcode_bin_candidates()
                      if c and os.path.isfile(c)), None)
    if not mcode_bin:
        return False, "未找到 mcode 可执行文件（PATH 与安装目录均无）"
    env = dict(os.environ)
    env.setdefault("TERM", "xterm-256color")
    env["COLUMNS"] = "100"
    env["LINES"] = "30"
    try:
        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe(mcode_bin, [mcode_bin], env)
    except (OSError, AttributeError) as e:
        return False, f"pty 启动失败: {e}"
    buf = b""
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            r, _, _ = select.select([fd], [], [], 1.0)
            if r:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    break
                if not data:
                    break
                buf += data
            text = buf.decode("utf-8", "replace")
            if any(k in text for k in SMOKE_CRASH_KEYWORDS):
                return False, text[:500]
            if len(buf) >= min_render_bytes:
                # 渲染帧已出现：再观察 1s 确认无迟发崩溃（崩溃信息随首帧同现）
                crash_wait = time.time() + 1
                while time.time() < crash_wait:
                    r2, _, _ = select.select([fd], [], [], 0.5)
                    if r2:
                        try:
                            buf += os.read(fd, 65536)
                        except OSError:
                            break
                    if any(k in buf.decode("utf-8", "replace") for k in SMOKE_CRASH_KEYWORDS):
                        return False, buf.decode("utf-8", "replace")[:500]
                return True, buf.decode("utf-8", "replace")[:500]
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except (OSError, AttributeError):
            pass
        try:
            os.waitpid(pid, os.WNOHANG)
        except (OSError, ChildProcessError):
            pass
    text = buf.decode("utf-8", "replace")
    if any(k in text for k in SMOKE_CRASH_KEYWORDS):
        return False, text[:500]
    if len(buf) == 0:
        return False, f"超时 {seconds}s 无任何输出（TUI 未能启动渲染）"
    return False, f"超时 {seconds}s 未渲染出首帧（仅 {len(buf)} 字节）"


class PatchAbort(Exception):
    """补丁流程中止（锚点失败/唯一性失败/冒烟失败等）。CLI 捕获后以 err() 退出；
    web 端点捕获后返回 400，不杀死服务进程。"""


def smoke_fail_and_rollback(original_content, head):
    """TUI 冒烟失败：回滚 cli.js 到 patch 前内容并抛 PatchAbort（含崩溃输出前 5 行）。"""
    try:
        with safe_write_open(CLI_PATH, MCODE_LIB, "w", encoding="utf-8") as f:
            f.write(original_content)
        print("error: TUI 启动冒烟失败，已自动回滚到 patch 前状态", file=sys.stderr)
    except OSError:
        if os.path.isfile(BACKUP_PATH):
            shutil.copy2(BACKUP_PATH, CLI_PATH)
        print("error: TUI 启动冒烟失败，回滚写入失败，已用官方备份恢复", file=sys.stderr)
    print("    TUI 输出（前 5 行）：", file=sys.stderr)
    for line in (head or "").splitlines()[:5]:
        print(f"      {line}", file=sys.stderr)
    raise PatchAbort("TUI 启动冒烟失败，已自动回滚到 patch 前状态")


def replace_once(content, old, new, label):
    """字符串替换唯一性断言：old 必须恰好出现 1 次，否则显式报错中止（不落盘）。"""
    n = content.count(old)
    if n != 1:
        raise PatchAbort(f"replace failed ({label}): 匹配 {n} 处，期望恰好 1 处，已中止（未落盘）")
    return content.replace(old, new, 1)


def replace_once_regex(content, pattern, repl, label):
    """正则替换唯一性断言：pattern 必须恰好匹配 1 处。repl 可为字符串或 callable。"""
    matches = list(re.finditer(pattern, content))
    if len(matches) != 1:
        raise PatchAbort(f"replace failed ({label}): 匹配 {len(matches)} 处，期望恰好 1 处，已中止（未落盘）")
    if callable(repl):
        return re.subn(pattern, repl, content, count=1)[0]
    return re.subn(pattern, repl, content, count=1)[0]

_HEX6 = re.compile(r"^[0-9A-Fa-f]{6}$")


def replace_once_fixed(content, prefix, inner, suffix, label):
    """固定前缀定位替换（C 级 find，避免 Python re 全量扫描 23MB）。"""
    i = content.find(prefix)
    if i == -1:
        raise PatchAbort(f"cannot find anchor: <{label}>（匹配 0 处，已中止不落盘）")
    if content.find(prefix, i + 1) != -1:
        raise PatchAbort(f"replace failed ({label}): 前缀匹配多处，已中止（未落盘）")
    j = content.find(suffix, i + len(prefix))
    if j == -1:
        raise PatchAbort(f"cannot find anchor: <{label}>（前缀后未找到 {suffix}）")
    return content[:i] + prefix + inner + content[j:]


def replace_fill_once(content, logo):
    """登录页 Logo fill 替换（find 定位 6 位 hex fill，唯一性断言）。"""
    hits = []
    start = 0
    while True:
        i = content.find('fill="#', start)
        if i == -1:
            break
        v = content[i + 7:i + 13]
        if len(v) == 6 and _HEX6.match(v) and content[i + 13:i + 14] == '"':
            hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise PatchAbort(f"replace failed (login logo fill): 匹配 {len(hits)} 处 hex fill，期望恰好 1 处，已中止（未落盘）")
    i = hits[0]
    return content[:i] + 'fill="' + logo + '"' + content[i + 14:]


def patch_apply(content, reps):
    """一次性拼接应用全部替换（性能优化）：reps = [(start, end, text)]，
    全部基于**原始 content 偏移**（插入型 start==end），按 start 稳定排序后
    单次 "".join——避免顺序替换造成多次 23MB 大字符串拼接（本环境每次 ~1.6s）。"""
    reps = sorted(reps, key=lambda r: r[0])
    parts = []
    pos = 0
    for st, en, text in reps:
        if st < pos:
            raise PatchAbort("patch 替换区间重叠，已中止（未落盘）")
        parts.append(content[pos:st])
        parts.append(text)
        pos = en
    parts.append(content[pos:])
    sep = b"" if isinstance(content, bytes) else ""
    return sep.join(parts)


def rep_fixed(content, prefix, inner, suffix, label):
    """定位 rep：固定前缀（唯一性断言）+ 后缀，返回 (start, end, text)。"""
    i = content.find(prefix)
    if i == -1:
        raise PatchAbort(f"cannot find anchor: <{label}>（匹配 0 处，已中止不落盘）")
    if content.find(prefix, i + 1) != -1:
        raise PatchAbort(f"replace failed ({label}): 前缀匹配多处，已中止（未落盘）")
    j = content.find(suffix, i + len(prefix))
    if j == -1:
        raise PatchAbort(f"cannot find anchor: <{label}>（前缀后未找到 {suffix}）")
    return (i, j + 1, prefix + inner + suffix)


def rep_fill(content, logo):
    """定位 rep：登录页 Logo fill（唯一 hex fill 断言，bytes 版）。"""
    if isinstance(logo, str):
        logo = logo.encode("ascii")
    hits = []
    start = 0
    while True:
        i = content.find(b'fill="#', start)
        if i == -1:
            break
        v = content[i + 7:i + 13]
        if len(v) == 6 and b"0123456789abcdefABCDEF".translate(
                None, v).decode("latin-1").isalnum() is False:
            pass  # 仅 ASCII 校验兜底
        if len(v) == 6 and all(c in b"0123456789abcdefABCDEF" for c in v) \
                and content[i + 13:i + 14] == b'"':
            hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise PatchAbort(f"replace failed (login logo fill): 匹配 {len(hits)} 处 hex fill，期望恰好 1 处，已中止（未落盘）")
    return (hits[0], hits[0] + 14, b'fill="' + logo + b'"')


def rep_regex(content, pattern, repl, label):
    """定位 rep：正则唯一匹配（匹配≠1 中止），repl 可为字符串或 callable。"""
    matches = list(re.finditer(pattern, content))
    if len(matches) != 1:
        raise PatchAbort(f"replace failed ({label}): 匹配 {len(matches)} 处，期望恰好 1 处，已中止（未落盘）")
    m = matches[0]
    return (m.start(), m.end(), repl(m) if callable(repl) else repl)


def rep_str(content, old, new, label):
    """定位 rep：唯一字符串替换。"""
    n = content.count(old)
    if n != 1:
        raise PatchAbort(f"replace failed ({label}): 匹配 {n} 处，期望恰好 1 处，已中止（未落盘）")
    i = content.find(old)
    return (i, i + len(old), new)




# ================================================================
# 原生主题后端（mcode >= 0.7.0）
#   主题文件： <dataDir>/tui/themes/<name>.json
#   选中项：   <dataDir>/tui/tui-settings.json  {"theme": "<id>"}
#   mcode 监听 themes/ 目录，热重载，无需重启。
# ================================================================

def _rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _blend(fg, bg, ratio):
    """把 fg 按 ratio 混到 bg 上，返回 #RRGGBB。"""
    f, b = _rgb(fg), _rgb(bg)
    return "#%02X%02X%02X" % tuple(
        max(0, min(255, int(round(b[i] + (f[i] - b[i]) * ratio)))) for i in range(3))


def _read_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_settings(patch):
    """原子更新 tui-settings.json（值为 None 表示删除该键）。"""
    data = _read_settings()
    for k, v in patch.items():
        if v is None:
            data.pop(k, None)
        else:
            data[k] = v
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    tmp = sanitize_path("%s.%d.tmp" % (SETTINGS_FILE, os.getpid()), TUI_DIR)
    with safe_write_open(tmp, TUI_DIR, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, SETTINGS_FILE)
    return data


def to_native_theme(theme):
    """mcode-theme 主题 → mcode 原生主题对象（严格 schema）。

    - 只保留 native schema 允许的键（ansi/logo/logoStyle 会被 mcode 拒绝）
    - 0.7.0 新增的 5 个 UI 键从主题自身调色板派生
    """
    app = theme["appearance"]
    ui = theme.get("colors") or {}
    syn = theme.get("syntax") or {}
    colors = {}
    for k in NATIVE_UI_KEYS:
        if k in ui and isinstance(ui[k], str) and HEX_RE.match(ui[k]):
            colors[k] = ui[k]
    # 派生 markdown / diff 键
    colors["markdownHeading"] = syn.get("mauve") or colors.get("accent") \
        or DEFAULT_UI[app]["markdownHeading"]
    colors["markdownCode"] = syn.get("green") or colors.get("success") \
        or DEFAULT_UI[app]["markdownCode"]
    colors["markdownLink"] = syn.get("blue") or colors.get("brand") \
        or DEFAULT_UI[app]["markdownLink"]
    bg = colors.get("userMessageBg") or DEFAULT_UI[app]["userMessageBg"]
    colors["diffAddedBg"] = _blend(colors.get("success") or DEFAULT_UI[app]["success"],
                                   bg, 0.18)
    colors["diffRemovedBg"] = _blend(colors.get("error") or DEFAULT_UI[app]["error"],
                                     bg, 0.18)
    syntax = {}
    for k in SYNTAX_KEYS:
        v = syn.get(k)
        if isinstance(v, str) and HEX_RE.match(v):
            syntax[k] = v
    native = {"name": theme["name"], "appearance": app,
              "colors": colors, "syntax": syntax}
    # vars：mcode 原生支持「颜色值引用 vars 中的名字」，原样透传
    v = theme.get("vars")
    if isinstance(v, dict) and v:
        native["vars"] = {k: val for k, val in v.items()
                          if isinstance(val, str) and HEX_RE.match(val)}
    if theme.get("label"):
        native["label"] = str(theme["label"])[:40]
    if theme.get("description"):
        native["description"] = str(theme["description"])[:120]
    return native


def validate_native_theme(native):
    """按 mcode 原生 schema 校验（与 0.7.0 内置 Ajv schema 等价）。"""
    if not isinstance(native, dict):
        return "theme must be a JSON object"
    name = native.get("name")
    if not isinstance(name, str) or not NATIVE_NAME_RE.match(name):
        return "name must match ^[a-z0-9][a-z0-9._-]{0,63}$"
    if name.lower() in BUILTIN_THEME_IDS:
        return "\"%s\" is a built-in theme id and is ignored" % name
    if native.get("appearance") not in ("dark", "light"):
        return "appearance must be 'dark' or 'light'"
    if native.get("label") is not None and not (
            isinstance(native["label"], str) and 1 <= len(native["label"]) <= 40):
        return "label must be a string of 1..40 characters"
    if native.get("description") is not None and not (
            isinstance(native["description"], str) and len(native["description"]) <= 120):
        return "description must be a string of at most 120 characters"
    vs = native.get("vars")
    if vs is not None:
        if not isinstance(vs, dict):
            return "vars must be an object"
        for k, val in vs.items():
            if not isinstance(val, str) or not HEX_RE.match(val):
                return "vars.%s must be a hex color" % k
    for key, allowed in (("colors", NATIVE_UI_KEYS), ("syntax", SYNTAX_KEYS)):
        block = native.get(key)
        if block is None:
            continue
        if not isinstance(block, dict):
            return "%s must be an object" % key
        for k, v in block.items():
            if k not in allowed:
                return "%s.%s is not an allowed key" % (key, k)
            # 原生 schema 允许：hex / 空串 / vars 引用名
            if not isinstance(v, str):
                return "%s.%s must be a string" % (key, k)
            if v == "" or HEX_RE.match(v) or re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", v):
                continue
            return "%s.%s must be a hex color like #RRGGBB" % (key, k)
    return None


def write_native_theme(native):
    """写入原生主题文件（mcode 会自动发现并热重载）。"""
    err_msg = validate_native_theme(native)
    if err_msg:
        err("native theme invalid: %s" % err_msg)
    os.makedirs(THEME_DIR, exist_ok=True)
    dest = sanitize_path(
        native_theme_path(native["name"], native.get("appearance")), THEME_DIR)
    tmp = sanitize_path("%s.%d.tmp" % (dest, os.getpid()), THEME_DIR)
    with safe_write_open(tmp, THEME_DIR, "w", encoding="utf-8") as f:
        json.dump(native, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, dest)
    return dest


def native_theme_path(name, appearance=None):
    """原生主题文件路径。

    mcode 按主题 JSON 的 name 字段分组，所以同一主题的明暗变体必须**同名**，
    但文件名要区分开，否则会互相覆盖：
      dark  → <name>.json
      light → <name>.light.json
    """
    if appearance == "light":
        return os.path.join(THEME_DIR, "%s.light.json" % sanitize_theme_name(name))
    return os.path.join(THEME_DIR, "%s.json" % sanitize_theme_name(name))


def _theme_files(directory):
    """目录下全部主题 JSON 路径（跳过隐藏文件与非 .json）。"""
    if not os.path.isdir(directory):
        return []
    out = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".json") or fn.startswith("."):
            continue
        p = os.path.join(directory, fn)
        if os.path.isfile(p):
            out.append(p)
    return out


def _theme_name_of(path):
    """从主题文件读 name 字段（失败回退到文件名）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        n = data.get("name")
        if isinstance(n, str) and n.strip():
            return n.strip()
    except (OSError, ValueError):
        pass
    return os.path.splitext(os.path.basename(path))[0]


def native_theme_names():
    """原生目录里的主题名（按 name 字段去重，明暗变体算同一个主题）。"""
    names = {}
    for p in _theme_files(THEME_DIR):
        names.setdefault(_theme_name_of(p), p)
    return sorted(names)


def lib_theme_names():
    """主题库里的主题名（按 name 字段去重）。"""
    names = {}
    for p in _theme_files(LIB_DIR):
        names.setdefault(_theme_name_of(p), p)
    return sorted(names)


def theme_variants(name, directory=None):
    """某主题的全部变体：[(appearance, 文件路径), ...]。

    mcode 按主题 JSON 的 name 字段分组，同名 + 不同 appearance 视为
    同一主题的明暗两个变体（选择器里可用 ←/→ 切外观）。

    查找顺序：主题库（可编辑源）→ 原生目录（输出）。源优先，否则 Web 端
    改色后写进原生目录的内容会被 apply 当成"原始主题"回灌，覆盖真正的设计稿。
    """
    out = []
    for d in ([directory] if directory else [LIB_DIR, THEME_DIR]):
        for p in _theme_files(d):
            if _theme_name_of(p) != name:
                continue
            app = None
            try:
                with open(p, "r", encoding="utf-8") as f:
                    app = json.load(f).get("appearance")
            except (OSError, ValueError):
                pass
            out.append((app or "dark", p))
    # 同 appearance 去重（先出现的优先）
    seen = set()
    uniq = []
    for app, p in out:
        if app in seen:
            continue
        seen.add(app)
        uniq.append((app, p))
    return uniq


def find_theme_file(name, appearance=None):
    """查找主题文件：优先原生目录，其次主题库；appearance 缺省取主变体。"""
    variants = theme_variants(name)
    if appearance:
        for app, p in variants:
            if app == appearance:
                return p
    if variants:
        # 主变体优先 dark
        for app, p in variants:
            if app == "dark":
                return p
        return variants[0][1]
    for d in (LIB_DIR, THEME_DIR):
        p = os.path.join(d, "%s.json" % name)
        if os.path.isfile(p):
            return p
    return None


def selected_theme_id():
    """当前 mcode 选中的主题 id（含 /dark|/light 外观覆盖）。"""
    v = _read_settings().get("theme")
    if not isinstance(v, str):
        return None
    v = v.strip()
    return v or None


def record_applied(theme_name, native=None):
    """记录 apply 元数据（不再依赖 cli.js 指纹）。"""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with safe_write_open(CURRENT_FILE, STATE_DIR, "w", encoding="utf-8") as f:
            json.dump({"name": theme_name,
                       "appearance": (native or {}).get("appearance"),
                       "time": int(__import__("time").time())},
                      f, indent=2, ensure_ascii=False)
        with safe_write_open(LAST_APPLIED_FILE, STATE_DIR, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name,
                       "time": int(__import__("time").time()),
                       "mcodeVersion": cli_fingerprint().get("version")},
                      f, indent=2, ensure_ascii=False)
    except OSError:
        pass



def load_theme(path):
    if not os.path.isfile(path):
        err(f"theme file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_theme_dict(data, path)


def load_theme_dict(data, path=None):
    """解析主题对象（兼容 mcode 原生 20 键格式与旧版 15 键格式）。"""
    if not isinstance(data, dict):
        err("theme must be a JSON object")
    name = data.get("name") or (os.path.splitext(os.path.basename(path))[0]
                                 if path else None)
    if not name:
        err("theme must have a 'name'")
    appearance = data.get("appearance", "dark")
    if appearance not in ("dark", "light"):
        err("theme 'appearance' must be 'dark' or 'light'")

    # UI colors（兼容 mcode 原生 20 键与旧版 15 键）
    colors = data.get("colors") or {}
    merged_ui = dict(DEFAULT_UI[appearance])
    unknown = []
    for k, v in colors.items():
        if k not in UI_KEYS:
            unknown.append(k)
            continue
        if not isinstance(v, str) or not HEX_RE.match(v):
            err(f"color '{k}' must be a hex color like #RRGGBB, got: {v!r}")
        merged_ui[k] = v
    if unknown:
        print(f"warning: ignoring unknown theme keys: {', '.join(unknown)}")

    # ANSI fallback colors (optional, no userMessageBg in official)
    ansi = data.get("ansi")
    merged_ansi = dict(DEFAULT_ANSI[appearance])
    if ansi:
        for k, v in ansi.items():
            if k in merged_ansi and isinstance(v, str) and ANSI_RE.match(v):
                merged_ansi[k] = v
            else:
                err(f"ansi color '{k}' must be an ANSI name like 'redBright'")

    # Syntax highlight colors (optional)
    syntax = data.get("syntax")
    merged_syntax = dict(DEFAULT_SYNTAX[appearance])
    if syntax:
        for k, v in syntax.items():
            if k in SYNTAX_KEYS and isinstance(v, str) and HEX_RE.match(v):
                merged_syntax[k] = v
            else:
                err(f"syntax color '{k}' must be a hex color like #RRGGBB")

    # Login page logo color (optional, default = brand)
    logo = data.get("logo")
    if logo is not None and (not isinstance(logo, str) or not HEX_RE.match(logo)):
        err(f"logo must be a hex color like #RRGGBB")
    merged_logo = logo or merged_ui["brand"]

    return {"name": name, "appearance": appearance,
            "colors": merged_ui, "ansi": merged_ansi,
            "syntax": merged_syntax, "logo": merged_logo,
            "label": data.get("label"), "description": data.get("description"),
            "vars": data.get("vars")}


def fmt(obj, keys):
    return "{" + ",".join(f'{k}:"{obj[k]}"' for k in keys if k in obj) + "}"


def fmt_ansi(obj, keys):
    return ",".join(f'{k}:"{obj[k]}"' for k in keys if k in obj)


def ensure_backup():
    if os.path.exists(BACKUP_PATH):
        return
    if not os.path.isfile(CLI_PATH):
        err(f"cli.js not found at {CLI_PATH}. Is mcode installed?")
    shutil.copy2(CLI_PATH, BACKUP_PATH)
    print(f"backup created: {BACKUP_PATH}")


def cli_fingerprint():
    """返回 (mcode 版本, cli.js md5) 用于检测 mcode 升级覆盖"""
    import hashlib
    md5 = None
    try:
        with open(CLI_PATH, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
    except OSError:
        pass
    version = None
    # 从 package.json 读取 mcode 版本（cli.js 头部的 version 是依赖库的）
    try:
        pkg_path = os.path.join(MCODE_LIB, "package.json")
        with open(pkg_path, "r", encoding="utf-8") as f:
            version = json.load(f).get("version")
    except OSError:
        pass
    return {"version": version, "md5": md5}


def cli_sha256():
    """cli.js SHA256 指纹（用于 update 检测 mcode 升级）"""
    import hashlib
    try:
        with open(CLI_PATH, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def record_last_applied(theme_name):
    """apply 时记录元数据（原生机制：~/.minimax/mcode-theme/.last-applied.json）"""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        data = {
            "fingerprint": cli_sha256(),
            "theme": theme_name,
            "time": int(__import__("time").time()),
        }
        with safe_write_open(LAST_APPLIED_FILE, STATE_DIR, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def update_check():
    """`mcode-theme update`：检查 mcode 版本变化（原生机制无需重新 apply）。"""
    if not os.path.isfile(LAST_APPLIED_FILE):
        print("尚未记录 apply 指纹（~/.minimax/themes/.last-applied.json 不存在）。")
        print("运行一次 mcode-theme apply <name> 后，即可用本命令检测 mcode 升级。")
        return
    try:
        with open(LAST_APPLIED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        print("warning: .last-applied.json 无法解析，请重新 apply 一次。")
        return
    theme_name = data.get("theme") or "(unknown)"
    ver = cli_fingerprint().get("version")
    old_ver = data.get("mcodeVersion")
    if ver and old_ver and ver != old_ver:
        print(f"mcode 已升级（{old_ver} -> {ver}）；"
              f"原生主题无需重新 apply，如需刷新可执行 mcode-theme apply {theme_name}")
    else:
        print(f"已是最新（主题 '{theme_name}' 仍有效）")


def check_stale():
    """检测 mcode 升级或主题文件缺失（原生机制）"""
    fp = cli_fingerprint()
    cur = current()
    if not cur:
        return
    if not find_theme_file(cur["name"]):
        print(f"warning: 主题文件 '{cur['name']}' 不存在，需要重新安装："
              f"mcode-theme apply {cur['name']}")


def cli_fingerprint_matches_backup():
    """当前 cli.js 是否与官方备份一致（说明被 mcode 升级/覆盖）"""
    import hashlib
    if not os.path.isfile(BACKUP_PATH):
        return False
    try:
        with open(CLI_PATH, "rb") as f:
            cur = hashlib.md5(f.read()).hexdigest()
        with open(BACKUP_PATH, "rb") as f:
            bak = hashlib.md5(f.read()).hexdigest()
        return cur == bak
    except OSError:
        return False


def read_cli():
    """读取当前 cli.js 原文（无任何校验）。"""
    if not os.path.isfile(CLI_PATH):
        err(f"cli.js not found at {CLI_PATH}. Is mcode installed?")
    with open(CLI_PATH, "r", encoding="utf-8") as f:
        return f.read()


def verify_mcode():
    if not os.path.isfile(CLI_PATH):
        err(f"cli.js not found at {CLI_PATH}. Is mcode installed?")
    with open(CLI_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    checks = [
        (r'id:"minimax",appearance:"dark",colors:Object\.freeze\(\{[^}]*\}\)', "UI dark"),
        (r'id:"minimax",appearance:"light",colors:Object\.freeze\(\{[^}]*\}\)', "UI light"),
        (r'Object\.freeze\(\{brand:"[a-zA-Z]+",[^}]*\}\)', "ANSI dark"),
        (r'Object\.freeze\(\{brand:"[a-zA-Z]+",[^}]*\}\)', "ANSI light"),
        (r'\{blue:"#[0-9A-Fa-f]{6}",[^}]*\}', "syntax dark"),
        (r'\{blue:"#[0-9A-Fa-f]{6}",[^}]*\}', "syntax light"),
    ]
    for pattern, label in checks:
        if not re.search(pattern, content):
            err(f"cannot find {label} theme block in cli.js (version mismatch?)")
    return content


def patch_cli(theme):
    ensure_backup()
    # bytes 全流程（读/写/拼接/指纹）：23MB 无 decode 开销（str 读 2.5s → 0.05s）
    with open(CLI_PATH, "rb") as f:
        content = f.read()
    original_content = content
    appearance = theme["appearance"]
    reps = []

    def A(s):
        return s.encode("ascii")

    # 1. UI hex theme
    ui_str = A(fmt(theme["colors"], UI_KEYS)[1:-1])
    reps.append(rep_fixed(content,
                          A('id:"minimax",appearance:"%s",colors:Object.freeze({' % appearance),
                          ui_str, A("}"), "UI hex theme"))

    # 2. ANSI fallback theme (colorLevel=1)
    ansi_inner = A(fmt_ansi(theme["ansi"], UI_KEYS))
    reps.append(rep_fixed(content, A('%s:Object.freeze({' % appearance),
                          ansi_inner, A("}"), "ANSI fallback theme"))

    # 3. Syntax highlight theme（prefix 以 blue:" 结尾，inner 从 hex 值开始）
    syntax_str = A(fmt(theme["syntax"], SYNTAX_KEYS)[len('{blue:"'):-1])
    reps.append(rep_fixed(content, A('%s:{blue:"' % appearance),
                          syntax_str, A("}"), "syntax highlight theme"))

    # 4. Login page logo color (hardcoded #7DC6FF originally)
    reps.append(rep_fill(content, A(theme["logo"])))

    # 5. Plan mode theme hook (Shift+Tab 切换 plan 模式时换主题)
    cur = current()
    plan_name = (cur or {}).get("planTheme") if cur else None
    plan_obj = None
    if plan_name:
        plan_path = os.path.join(THEME_DIR, f"{plan_name}.json")
        if os.path.isfile(plan_path):
            plan_obj = load_theme(plan_path)

    # 5a. 注入 plan 主题对象（顶层 var 声明，所有模块可见）
    plan_anchor_matches = list(re.finditer(rb'var [A-Za-z_$][\w$]*=Object\.create;', content))
    if len(plan_anchor_matches) != 1:
        raise PatchAbort(f"cannot find anchor: <top-level Object.create holder>（匹配 {len(plan_anchor_matches)} 处，期望 1）——mcode 结构可能已变化，中止且不落盘")
    anchor_m = plan_anchor_matches[0]
    cur_colors = fmt(theme["colors"], UI_KEYS)
    cur_app = theme.get("appearance", "dark")
    cur_theme_lit = ('Object.freeze({id:"minimax-current",appearance:"%s",colors:Object.freeze(%s)})'
                     % (cur_app, cur_colors))
    plan_var_re = rb'var __mcodePlanThemeActive=!1,__mcodePlanTheme=[^;]*?,__mcodeCurrentTheme=[^;]*?;'
    if plan_obj:
        plan_colors = fmt(plan_obj["colors"], UI_KEYS)
        plan_obj_lit = ('Object.freeze({id:"minimax-plan",'
                        'appearance:"%s",colors:Object.freeze(%s)})' % (plan_obj["appearance"], plan_colors))
        if b'__mcodePlanThemeActive' not in content:
            inject = A('var __mcodePlanThemeActive=!1,__mcodePlanTheme=%s,__mcodeCurrentTheme=%s;' % (plan_obj_lit, cur_theme_lit))
            reps.append((anchor_m.start(), anchor_m.end(), anchor_m.group(0) + inject))
        else:
            reps.append(rep_regex(content, plan_var_re,
                                  A('var __mcodePlanThemeActive=!1,__mcodePlanTheme=%s,__mcodeCurrentTheme=%s;' % (plan_obj_lit, cur_theme_lit)),
                                  "plan hook 更新（保留 planTheme）"))
    else:
        if b'__mcodePlanThemeActive' not in content:
            inject = A('var __mcodePlanThemeActive=!1,__mcodePlanTheme=null,__mcodeCurrentTheme=%s;' % cur_theme_lit)
            reps.append((anchor_m.start(), anchor_m.end(), anchor_m.group(0) + inject))
        else:
            reps.append(rep_regex(content, plan_var_re,
                                  A('var __mcodePlanThemeActive=!1,__mcodePlanTheme=null,__mcodeCurrentTheme=%s;' % cur_theme_lit),
                                  "plan hook 重置（无 planTheme）"))
    plan_block_end = anchor_m.end()

    # 5b. 修改主题应用函数开头（jri/gai，版本无关）：plan 激活时用 plan 主题
    m_theme_fn = re.search(
        rb'function ([A-Za-z_$][\w$]*)\(t,e\)\{if\(!\(([A-Za-z_$][\w$]*)\.name!==t\.id\|\|'
        rb'\2\.appearance!==t\.appearance\|\|\2\.colorLevel!==e\)\)return!1;',
        content)
    if b'__mcodePlanThemeActive&&__mcodePlanTheme' not in content:
        if not m_theme_fn:
            raise PatchAbort("cannot find anchor: <theme apply function>（mcode 结构变化，中止且不落盘）")
        fn = m_theme_fn.group(1).decode()
        var = m_theme_fn.group(2).decode()
        new = A('function %s(t,e){if(__mcodePlanThemeActive&&__mcodePlanTheme){'
                't={id:__mcodePlanTheme.id,appearance:__mcodePlanTheme.appearance,colors:__mcodePlanTheme.colors};}'
                'if(!(%s.name!==t.id||%s.appearance!==t.appearance||%s.colorLevel!==e))return!1;'
                % (fn, var, var, var))
        reps.append((m_theme_fn.start(), m_theme_fn.end(), new))
    else:
        fn = m_theme_fn.group(1).decode() if m_theme_fn else 'gai'

    # 5c. 修改 plan 状态渲染函数开头（gni/Jai，版本无关）：检测 plan 切换并刷新主题
    m_plan_fn = re.search(
        rb'function ([A-Za-z_$][\w$]*)\(t,e=!1\)\{if\(t\.planMode!=="plan"&&!t\.planModeTransition\)return"";',
        content)
    if b'typeof __mcodePlanThemeActive==="boolean"' not in content:
        if not m_plan_fn:
            raise PatchAbort("cannot find anchor: <plan status render function>（中止且不落盘）")
        pfn = m_plan_fn.group(1).decode()
        new = A('function %s(t,e=!1){if(typeof __mcodePlanThemeActive==="boolean"){'
                'var np=t.planMode==="plan"||t.planModeTransition==="next-message"||t.planModeTransition==="submitting";'
                'if(np!==__mcodePlanThemeActive){__mcodePlanThemeActive=np;'
                'try{__mcodeThemeRefresh()}catch(_){}}}'
                'if(t.planMode!=="plan"&&!t.planModeTransition)return"";'
                % pfn)
        reps.append((m_plan_fn.start(), m_plan_fn.end(), new))

        # 5c2. 顶层注入 __mcodeThemeRefresh 辅助函数（追加在 plan 块之后）
        if b'function __mcodeThemeRefresh' not in content:
            refresh = A('function __mcodeThemeRefresh(){'
                        'var th=(__mcodePlanThemeActive&&__mcodePlanTheme)?__mcodePlanTheme:__mcodeCurrentTheme;'
                        'if(th){try{__mcodeThemeFn(th,__mcodeThemeLevel)}catch(_){}}}'
                        'var __mcodeThemeFn=%s,__mcodeThemeLevel=3;'
                        % fn)
            reps.append((plan_block_end, plan_block_end, refresh))

    # 5e. Logo 五段渐变插桩（上浅下深）：替换 Ent() 的离散 6 色数组为
    #     逐行五段渐变。段1=wordmarkHighlight → 段3=brand → 段5=wordmarkShadow，
    #     段2/段4 在线性 RGB 空间插值；兜底：hl−shadow 亮度差 <0.26 时 shadow
    #     ×0.85 迭代加深（保证相邻段亮度差 ≥0.06）；brand 亮度不在区间内或
    #     与任一端差 <0.122 时，段3 退化为线性中点。256 色（colorLevel<3）降级保留。
    # v0.1.4+ logo函数名为vst，使用FS.hero（非xS.hero）
    m_ent = re.search(
        rb'hero:{fullMinWidth:\d+,mediumMinWidth:\d+,microMinWidth:\d+,fallbackTitle:[^}]*}',
        content)
    if m_ent:
        grad_fn = (
            'function __mcodeLogoGradient5(rows,top,mid,bottom){'
            'var N=Math.max(1,rows),_ct=(process.env&&process.env.COLORTERM)||"",'
            '_term=(process.env&&process.env.TERM)||"",'
            '_modern=/xterm-256color|screen-256color|tmux-256color|kitty|alacritty|'
            'wezterm|iterm|st-256color|rxvt-unicode-256color|putty-256color/i,'
            'cl=(process.stdout&&process.stdout.isTTY)?'
            '((_ct.indexOf("truecolor")>=0||_ct.indexOf("24bit")>=0||'
            '(_ct!=="0"&&_ct!=="false"&&_ct!=="no"&&_modern.test(_term)))?24:'
            '(process.stdout.getColorDepth?process.stdout.getColorDepth():8)):8,'
            'full=cl>=24,out=[],i,t,s,f,c,hex,k;'
            'function hp(x){return{x:parseInt(x.slice(1,3),16),y:parseInt(x.slice(3,5),16),'
            'z:parseInt(x.slice(5,7),16)}}'
            'function fmt(a){var r=a.x.toString(16),g=a.y.toString(16),b=a.z.toString(16);'
            'return"#"+("0"+r).slice(-2)+("0"+g).slice(-2)+("0"+b).slice(-2)}'
            'function lerp(a,b,t){return{x:Math.round(a.x+(b.x-a.x)*t),'
            'y:Math.round(a.y+(b.y-a.y)*t),z:Math.round(a.z+(b.z-a.z)*t)}}'
            'function idx256(a){var r=Math.round(a.x/255*5),g=Math.round(a.y/255*5),'
            'b=Math.round(a.z/255*5);return 16+36*r+6*g+b}'
            'var A=hp(top),B=hp(mid),C=hp(bottom);'
            'var S1=A,S2=lerp(A,B,0.5),S3=B,S4=lerp(B,C,0.5),S5=C,SEGS=[S1,S2,S3,S4,S5];'
            'var SEGIDX=[idx256(S1),idx256(S2),idx256(S3),idx256(S4),idx256(S5)];'
            'for(k=1;k<5;k++){var g=0,sc={x:SEGS[k].x,y:SEGS[k].y,z:SEGS[k].z};'
            'while(g<8){var dupe=!1;for(var pi=0;pi<k;pi++){'
            'if(idx256(sc)===SEGIDX[pi]){dupe=!0;break}}'
            'if(!dupe){SEGIDX[k]=idx256(sc);break}'
            'var sv=[sc.x,sc.y,sc.z],'
            'chans=[0,1,2].sort(function(a,b){return sv[a]-sv[b]}),moved=!1;'
            'for(var ci=0;ci<3&&!moved;ci++){var ch=chans[ci],'
            'base=Math.floor((ch===0?sc.x:ch===1?sc.y:sc.z)/51)*51;'
            'if(base>0){if(ch===0){sc.x=base-1}else if(ch===1){sc.y=base-1}'
            'else{sc.z=base-1}moved=!0}}'
            'if(!moved){break}g++}}'
            'for(i=0;i<N;i++){t=N===1?0.5:i/(N-1);'
            'if(full){s=Math.min(4,Math.floor(t*4));f=t*4-s;'
            'c=lerp(SEGS[s],SEGS[Math.min(4,s+1)],f);'
            'hex=fmt(c);out.push("\\x1b[38;2;"+c.x+";"+c.y+";"+c.z+"m")}'
            'else{out.push("\\x1b[38;5;"+SEGIDX[Math.min(4,Math.floor(t*4))]+"m")}}return out}'
        ).encode('ascii')
        if b'__mcodeLogoGradient5' not in content:
            # 注入到 __mcodeThemeFn 变量声明之后（避免与 plan 块 refresh 注入重叠）
            m_tf = re.search(rb'var __mcodeThemeFn=[^;]*;', content)
            grad_insert = m_tf.end() if m_tf else plan_block_end
            reps.append((grad_insert, grad_insert, grad_fn))
        else:
            # 已有 v5 插桩（可能为旧版本）：整体替换函数体，保证升级生效
            reps.append(rep_regex(content,
                                  rb'function __mcodeLogoGradient5\(rows,top,mid,bottom\)\{.*\}return out\}',
                                  lambda m: grad_fn, "__mcodeLogoGradient5 函数体升级"))
        # 替换 Ent 的 l 数组（兼容旧版 __mcodeLogoGradient 三段插桩：一并换为五段）
        # v0.1.4+ 变量名为 de（非旧版 me）
        _v = rb'(?:de|me|ce)'  # 兼容三种变量名
        new_l = A('l=__mcodeLogoGradient5(a.length,ce.wordmarkHighlight,ce.brand,ce.wordmarkShadow)')
        new_l_me = A('l=__mcodeLogoGradient5(a.length,me.wordmarkHighlight,me.brand,me.wordmarkShadow)')
        new_l_de = A('l=__mcodeLogoGradient5(a.length,de.wordmarkHighlight,de.brand,de.wordmarkShadow)')
        if new_l not in content and new_l_me not in content and new_l_de not in content:
            old_l3_ce = A('l=__mcodeLogoGradient(a.length,ce.wordmarkHighlight,ce.brand,ce.wordmarkShadow)')
            old_l3_de = A('l=__mcodeLogoGradient(a.length,de.wordmarkHighlight,de.brand,de.wordmarkShadow)')
            old_l3_me = A('l=__mcodeLogoGradient(a.length,me.wordmarkHighlight,me.brand,me.wordmarkShadow)')
            if old_l3_ce in content:
                reps.append(rep_str(content, old_l3_ce, new_l, "Ent logo l-array (v3→v5, ce)"))
            elif old_l3_de in content:
                reps.append(rep_str(content, old_l3_de, new_l, "Ent logo l-array (v3→v5, de)"))
            elif old_l3_me in content:
                reps.append(rep_str(content, old_l3_me, new_l, "Ent logo l-array (v3→v5, me)"))
            else:
                old_l_ce = A('l=[ce.wordmarkHighlight,ce.wordmarkHighlight,ce.brand,ce.brand,ce.wordmarkShadow,ce.wordmarkShadow]')
                old_l_de = A('l=[de.wordmarkHighlight,de.wordmarkHighlight,de.brand,de.brand,de.wordmarkShadow,de.wordmarkShadow]')
                old_l_me = A('l=[me.wordmarkHighlight,me.wordmarkHighlight,me.brand,me.brand,me.wordmarkShadow,me.wordmarkShadow]')
                if old_l_ce in content:
                    reps.append(rep_str(content, old_l_ce, new_l, "Ent logo l-array (raw, ce)"))
                elif old_l_de in content:
                    reps.append(rep_str(content, old_l_de, new_l, "Ent logo l-array (raw, de)"))
                elif old_l_me in content:
                    reps.append(rep_str(content, old_l_me, new_l, "Ent logo l-array (raw, me)"))
                else:
                    raise PatchAbort("cannot find anchor: <Ent logo l-array>（中止且不落盘）")
        # 每行用渐变序列号（m 取 l[m]，l 长度=行数，无需 %7；保留 fallback）
        # v0.1.4+ 使用Zfn（非旧版dun）；兼容已有 p.startsWith 补丁
        old_map_zfn_raw = A('m=d%7,p=s?l[m]??de.brand:de.brand;return RAn(he.bold.hex(p)(u),t)')
        old_map_zfn_me = A('m=d%7,p=s?l[m]??me.brand:me.brand;return RAn(he.bold.hex(p)(u),t)')
        old_map_zfn_ce = A('m=d%7,p=s?l[m]??ce.brand:ce.brand;return RAn(he.bold.hex(p)(u),t)')
        old_map_dun_raw = A('m=d%7,p=s?l[m]??de.brand:de.brand;return dun(ye.bold.hex(p)(u),t)')
        old_map_dun_me = A('m=d%7,p=s?l[m]??me.brand:me.brand;return dun(ye.bold.hex(p)(u),t)')
        old_map_dun_ce = A('m=d%7,p=s?l[m]??ce.brand:ce.brand;return dun(pe.bold.hex(p)(u),t)')
        old_map_dun_patch = A('m=d%7,p=s?(l[m]??me.brand):me.brand;return p&&p.startsWith("\\x1b")?'
                              'dun(p+u+"\\x1b[0m",t):dun(ye.bold.hex(p)(u),t)')
        old_map_ce_simple = A('m=d%7,p=s?l[m]??ce.brand:ce.brand;return RAn(pe.bold.hex(p)(u),t)')
        new_map = A('m=d%7,p=s?(l[m]??de.brand):de.brand;return p&&p.startsWith("\\x1b")?'
                    'RAn(p+u+"\\x1b[0m",t):RAn(he.bold.hex(p)(u),t)')
        new_map_me = A('m=d%7,p=s?(l[m]??me.brand):me.brand;return p&&p.startsWith("\\x1b")?'
                       'RAn(p+u+"\\x1b[0m",t):RAn(he.bold.hex(p)(u),t)')
        new_map_ce = A('m=d%7,p=s?(l[m]??ce.brand):ce.brand;return p&&p.startsWith("\\x1b")?'
                       'RAn(p+u+"\\x1b[0m",t):RAn(he.bold.hex(p)(u),t)')
        # 按优先级尝试匹配
        for old, new, label in [
            (old_map_zfn_raw, new_map, "raw Zfn→Zfn"),
            (old_map_zfn_me, new_map_me, "me Zfn→Zfn"),
            (old_map_zfn_ce, new_map_ce, "ce Zfn→Zfn"),
            (old_map_dun_raw, new_map, "raw dun→Zfn"),
            (old_map_dun_me, new_map_me, "me dun→Zfn"),
            (old_map_dun_ce, new_map_ce, "ce dun→Zfn"),
            (old_map_dun_patch, new_map_me, "me dun-patch→Zfn"),
            (old_map_ce_simple, new_map_ce, "ce simple→Zfn"),
        ]:
            if old in content:
                reps.append(rep_str(content, old, new, f"Ent 渐变行映射（{label}）"))
                break
        else:
            # 已经是目标形态则跳过
            if new_map not in content and new_map_me not in content and new_map_ce not in content:
                raise PatchAbort("cannot find anchor: <Ent gradient row map>（中止且不落盘）")

    # 一次性拼接（避免多次 23MB 大字符串拼接）
    content = patch_apply(original_content, reps)

    # 内容级一致性判断：生成的目标内容与当前 cli.js 完全一致 → 不写盘、不校验
    # （锚点唯一性断言已在定位阶段保证替换目标明确；内容一致即上次验证过）
    if content == original_content:
        _record_apply_state(theme)
        print(f"installed theme '{theme['name']}' ({appearance}) - 内容一致，无需写盘")
        return

    with safe_write_open(CLI_PATH, MCODE_LIB, "wb") as f:
        f.write(content)

    # 记录状态 + 写入主题内容缓存（切回时缓存重放）
    _record_apply_state(theme)
    _write_theme_cache(theme["name"], content)
    print(f"installed theme '{theme['name']}' ({appearance}) - patched UI + ANSI + syntax")


def check_theme_disciplines(theme):
    """9 条纪律校验（与 validate-themes.py 同款）。
    返回 (warns, fails)；fails 非空即拒绝安装。"""
    # 优先复用 validate-themes.py（单一事实源）；缺失时内联兜底
    try:
        import importlib.util
        val_path = os.path.join(TOOL_DIR, "validate-themes.py")
        if os.path.isfile(val_path):
            if TOOL_DIR not in sys.path:
                sys.path.insert(0, TOOL_DIR)
            spec = importlib.util.spec_from_file_location("mcode_validate_mod", val_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.check_theme(theme)
    except Exception:
        pass
    return _inline_discipline_check(theme)


def _inline_discipline_check(theme):
    """内联 9 条纪律（validate-themes.py 不可用时的兜底）"""
    import colorsys as _cs
    c = theme.get("colors") or {}
    is_light = theme.get("appearance") == "light"
    fails, warns = [], []

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def lum(h):
        r, g, b = (v / 255.0 for v in hex_to_rgb(h))
        lin = tuple(v ** 2.2 for v in (r, g, b))
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def hue(h):
        r, g, b = (v / 255.0 for v in hex_to_rgb(h))
        hh, _, _ = _cs.rgb_to_hls(r, g, b)
        return hh * 360.0

    required = ["userMessageBg", "border", "line", "muted", "dim", "text",
                "brand", "accent", "signal", "wordmarkHighlight", "wordmarkShadow"]
    for k in required:
        if k not in c or not isinstance(c[k], str) or not c[k].startswith("#"):
            fails.append(f"纪律0: 缺少有效颜色键 {k}")

    def L(k):
        return lum(c[k]) if k in c and c[k].startswith("#") else -1

    if not is_light:
        for a, b in zip(["dim", "muted", "text"], ["muted", "text"]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1: 亮度序违反 {a} -> {b}")
        for a, b in zip(["userMessageBg", "border"], ["border", "line"]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1: 亮度序违反 {a} -> {b}")
    else:
        for a, b in zip(["text", "muted"], ["muted", "dim"]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1(light): 亮度序违反 {a} -> {b}")
        for a, b in zip(["line", "border"], ["border", "userMessageBg"]):
            if not (L(a) < L(b)):
                fails.append(f"纪律1(light): 亮度序违反 {a} -> {b}")
    for a, b in [("text", "muted"), ("text", "dim"), ("muted", "dim")]:
        if abs(L(a) - L(b)) < 0.10:
            fails.append(f"纪律2: {a}/{b} 亮度差 < 0.10")
    hues = [hue(c[k]) for k in ("userMessageBg", "border", "line")]
    for i in range(3):
        for j in range(i + 1, 3):
            d = min(abs(hues[i] - hues[j]), 360 - abs(hues[i] - hues[j]))
            if d > 25:
                fails.append(f"纪律3: 色相偏差 {d:.1f}°")
    for k in ("userMessageBg", "border", "line", "muted", "dim"):
        lv = L(k)
        if lv > 0.85 or lv < 0.05:
            continue
        _, s, _ = _cs.rgb_to_hls(*[v / 255.0 for v in hex_to_rgb(c[k])])
        if s > 0.45:
            fails.append(f"纪律4: {k} 饱和度 {s:.2f} > 0.45")
    if len({c["brand"], c["accent"], c["signal"]}) != 1:
        fails.append("纪律5: 品牌色族发散")
    try:
        from logo_styles import check_gradient as _cg
        fails.extend(_cg(c, c.get("userMessageBg")))
    except Exception as e:
        fails.append(f"纪律6-9: 渐变检查异常 {e}")
    return warns, fails


def install_from_source(source):
    """`mcode-theme install <URL|本地JSON>`。
    获取 → 9 条纪律校验 → FAIL 拒绝输出明细；通过 → 入库（不 patch，提示 apply）。"""
    import tempfile
    import urllib.request
    theme = None
    tmp = None
    try:
        if source.startswith("http://") or source.startswith("https://"):
            tmp = os.path.join(tempfile.gettempdir(),
                               f"mcode-theme-fetch-{os.getpid()}.json")
            with safe_urlopen(source, timeout=30) as r:   # SSRF 卡口（含校验）
                data = r.read(5 * 1024 * 1024 + 1)   # 上限 5MB
            if len(data) > 5 * 1024 * 1024:
                err("主题文件超过 5MB 上限")
            with safe_write_open(tmp, tempfile.gettempdir(), "wb") as f:
                f.write(data)
            theme = load_theme(tmp)
        else:
            # 入口清洗：本地来源路径规范化 + 解析符号链接
            theme = load_theme(os.path.realpath(os.path.abspath(source)))
    except Exception as e:
        err(f"无法读取主题来源 {source}: {e}")
    finally:
        if tmp and os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    warns, fails = check_theme_disciplines(theme)
    if fails:
        print(f"error: 主题 '{theme['name']}' 未通过纪律校验，已拒绝安装：", file=sys.stderr)
        for w in fails:
            print(f"    - {w}", file=sys.stderr)
        sys.exit(1)
    native = to_native_theme(theme)
    err_msg = validate_native_theme(native)
    if err_msg:
        print(f"error: 主题不符合 mcode 原生 schema：{err_msg}", file=sys.stderr)
        sys.exit(1)
    dest = write_native_theme(native)
    failed = {int(m.group(1)) for w in fails if (m := re.match(r"纪律(\d+)", w))}
    n = 13 - len(failed)  # 纪律 0-12 共 13 项
    print(f"已安装 {theme['name']}（{n}/{13} 纪律通过）→ mcode-theme apply {theme['name']}")
    print(f"saved native theme to {dest}")


CACHE_DIR = os.path.join(STATE_DIR, "cache")
CACHE_MAX = 3  # LRU：最多保留 3 个主题的 patch 结果（23MB×3 ≈ 69MB）


def _safe_cache_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name or "theme")


def _backup_sha256():
    import hashlib
    try:
        with open(BACKUP_PATH, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _record_apply_state(theme):
    """写 .current-theme.json（保留 planTheme）+ .last-applied.json（指纹）。"""
    prev = current() or {}
    theme = dict(theme)
    if prev.get("planTheme"):
        theme["planTheme"] = prev["planTheme"]
    fp = cli_fingerprint()
    if fp["md5"]:
        theme["_cliMd5"] = fp["md5"]
    if fp["version"]:
        theme["_cliVersion"] = fp["version"]
    with safe_write_open(CURRENT_FILE, STATE_DIR, "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2)
    record_last_applied(theme["name"])


def _write_theme_cache(name, content):
    """缓存该主题的 patch 结果（完整 cli.js 内容），LRU 保留 CACHE_MAX 个。
    元数据记录基线（官方备份 sha256），mcode 升级后缓存自动失效。"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        base = _safe_cache_name(name)
        with safe_write_open(os.path.join(CACHE_DIR, base + ".js"), CACHE_DIR, "wb") as f:
            f.write(content)
        with safe_write_open(os.path.join(CACHE_DIR, base + ".json"), CACHE_DIR, "w", encoding="utf-8") as f:
            json.dump({"baseline": _backup_sha256(), "theme": name,
                       "ts": int(time.time())}, f)
        # LRU 清理：保留最近 CACHE_MAX 个
        metas = []
        for fn in os.listdir(CACHE_DIR):
            if fn.endswith(".json") and fn != base + ".json":
                try:
                    m = json.load(open(os.path.join(CACHE_DIR, fn), encoding="utf-8"))
                    metas.append((m.get("ts", 0), fn[:-5]))
                except (json.JSONDecodeError, OSError):
                    metas.append((0, fn[:-5]))
        metas.sort(reverse=True)
        for _, stem in metas[CACHE_MAX - 1:]:
            for ext in (".js", ".json"):
                fp = os.path.join(CACHE_DIR, stem + ext)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                    except OSError:
                        pass
    except OSError:
        pass


def apply(name):
    """应用主题（原生机制）：把主题的全部变体写入 <dataDir>/tui/themes/ + 设置选中项。

    同名 + 不同 appearance 的文件视为同一主题的明暗变体，mcode 会把它们
    合并成一个主题条目，选择器里可用 ←/→ 切外观。
    """
    variants = theme_variants(name)
    if not variants:
        p = find_theme_file(name)
        if not p:
            err(f"theme '{name}' not found in {THEME_DIR} or {LIB_DIR}")
        variants = [("dark", p)]
    written = []
    main = None
    for app, path in variants:
        theme = load_theme(path)
        native = to_native_theme(theme)
        dest = write_native_theme(native)
        written.append((app, dest))
        if main is None or app == "dark":
            main = native
    _write_settings({"theme": name})
    record_applied(name, main)
    print(f"applied theme '{name}' -> {written[0][1]}")
    for app, dest in written[1:]:
        print(f"  + {app} variant -> {dest}")
    print(f"selected in {SETTINGS_FILE}")
    return main


def restore():
    """恢复官方默认主题（原生机制）：清除 tui-settings.json 的 theme 字段。

    mcode 会回落到内置 minimax 主题；已安装的主题文件保留，便于再次 apply。
    """
    _write_settings({"theme": None})
    for p in (CURRENT_FILE, LAST_APPLIED_FILE):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    print("restored official default theme（已清除 %s 的 theme 字段）" % SETTINGS_FILE)
    return


def _restore_legacy():
    """旧版（patch cli.js）恢复流程，仅供 mcode < 0.7.0 使用。
    恢复官方默认主题（加固）：
    1) 本地备份存在 → 用备份恢复（写前校验为官方原版）
    2) 备份缺失 → `npm root -g @minimax-ai/code` 定位 npm 全局包内 cli.js 还原
       （写前校验与 npm 包一致：官方主题块齐全且无注入标记），并重建备份
    3) npm 不可用/包缺失/文件非官方原版 → 明确指引 `npm i -g @minimax-ai/code 后重试`
    成功后清理 .current-theme.json / .last-applied.json（plan 注入变量随官方
    文件覆盖而消失，并显式校验无注入残留）。任一环节失败输出明确错误与下一步命令。
    """
    source_desc = None
    src = None
    if os.path.isfile(BACKUP_PATH):
        src, source_desc = BACKUP_PATH, "本地备份"
    else:
        cli_path, why = _npm_global_cli_path()
        if cli_path is None:
            print("error: 未找到本地备份 cli.js.minimax-original，且无法从 npm 全局包还原。", file=sys.stderr)
            print(f"    原因：{why}", file=sys.stderr)
            print("    下一步：npm i -g @minimax-ai/code 后重试 mcode-theme restore", file=sys.stderr)
            sys.exit(1)
        src, source_desc = cli_path, "npm 全局包"
    try:
        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"error: 读取恢复源失败（{src}）：{e}", file=sys.stderr)
        print("    下一步：npm i -g @minimax-ai/code 后重试 mcode-theme restore", file=sys.stderr)
        sys.exit(1)
    if not _is_official_cli(content):
        print("error: 恢复源 cli.js 非官方原版（含注入标记或主题块缺失），已中止恢复。", file=sys.stderr)
        print("    下一步：npm i -g @minimax-ai/code 后重试 mcode-theme restore", file=sys.stderr)
        sys.exit(1)
    try:
        shutil.copy2(src, CLI_PATH)
    except OSError as e:
        print(f"error: 覆盖 cli.js 失败：{e}", file=sys.stderr)
        print("    下一步：检查 mcode 目录权限后重试，或手动拷贝官方 cli.js 到安装目录", file=sys.stderr)
        sys.exit(1)
    # 重建备份（保留既有回滚管线语义）
    if not os.path.isfile(BACKUP_PATH):
        try:
            shutil.copy2(CLI_PATH, BACKUP_PATH)
        except OSError:
            pass
    # 清理配置残留：.current-theme.json / .last-applied.json
    for p in (CURRENT_FILE, LAST_APPLIED_FILE):
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError as e:
            print(f"warning: 清理 {p} 失败：{e}", file=sys.stderr)
    # 显式校验无注入残留（plan 变量等随官方文件覆盖消失）
    try:
        with open(CLI_PATH, "r", encoding="utf-8") as f:
            restored = f.read()
        markers = [m for m in ("__mcodePlanTheme", "__mcodeCurrentTheme",
                               "__mcodeLogoGradient5", "__mcodeThemeRefresh")
                   if m in restored]
        if markers:
            print(f"warning: 恢复后 cli.js 仍含注入标记 {markers}，建议重装 mcode 后重试", file=sys.stderr)
    except OSError:
        pass
    print(f"restored official default theme（来源：{source_desc}）")


# ================================================================
# 原生机制入口
# ================================================================


def _npm_global_cli_path():
    """`npm root -g @minimax-ai/code` 定位 npm 全局包内 cli.js。
    返回 (cli_path|None, 失败原因|None)。"""
    npm = shutil.which("npm")
    if not npm:
        return None, "npm 不在 PATH 中"
    try:
        r = subprocess.run([npm, "root", "-g", "@minimax-ai/code"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"npm 执行失败：{e}"
    if r.returncode != 0:
        return None, (r.stderr.strip() or r.stdout.strip() or "npm root -g 未找到该包")
    root = r.stdout.strip().splitlines()[-1]
    cli_path = os.path.join(root, "@minimax-ai", "code", "cli.js")
    if not os.path.isfile(cli_path):
        return None, f"npm 全局包内未找到 cli.js（{cli_path}）"
    return cli_path, None


def _is_official_cli(content):
    """官方原版 cli.js 判定：6 个主题块齐全 + 无本工具注入标记。"""
    markers = ("__mcodePlanTheme", "__mcodeCurrentTheme",
               "__mcodeLogoGradient5", "__mcodeThemeRefresh")
    if any(m in content for m in markers):
        return False
    checks = [
        r'id:"minimax",appearance:"dark",colors:Object\.freeze\(\{[^}]*\}\)',
        r'id:"minimax",appearance:"light",colors:Object\.freeze\(\{[^}]*\}\)',
        r'Object\.freeze\(\{brand:"[a-zA-Z]+",[^}]*\}\)',
        r'\{blue:"#[0-9A-Fa-f]{6}",[^}]*\}',
    ]
    return all(re.search(p, content) for p in checks)


def list_themes():
    print("Installed themes:")
    for n in native_theme_names():
        print(f"  - {n}")
    lib = [n for n in lib_theme_names() if n not in native_theme_names()]
    if lib:
        print("Library (not yet installed):")
        for n in lib:
            print(f"  - {n}")
    print("Built-in (mcode): %s" % ", ".join(BUILTIN_THEME_IDS))
    cur = current()
    if cur:
        line = f"Current: {cur['name']}"
        if cur.get("appearance"):
            line += f" ({cur['appearance']})"
        print(line)


def current():
    """当前选中的主题（读 mcode 的 tui-settings.json）。"""
    tid = selected_theme_id()
    if not tid:
        return None
    base = tid.split("/")[0]
    app = tid.split("/")[1] if "/" in tid else None
    if app is None:
        p = find_theme_file(base)
        if p:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    app = json.load(f).get("appearance")
            except (OSError, ValueError):
                app = None
    rec = {"name": base, "appearance": app, "planTheme": None, "_raw": tid}
    return rec


def current_status():
    """当前主题状态（供 CLI current 与 web /api/status）：
    {applied, name, planTheme, appliedAtMs, state}
    state: none（未应用）/ ok（指纹一致=生效）/ stale（cli.js 指纹已变更=需重新 apply）"""
    cur = current()
    status = {"applied": bool(cur), "name": cur and cur.get("name"),
              "planTheme": cur and cur.get("planTheme"),
              "appliedAtMs": None, "state": "none"}
    if not cur:
        return status
    # 原生机制：状态由主题文件是否存在 + mcode 版本决定
    p = find_theme_file(cur["name"])
    status["state"] = "ok" if p and os.path.isfile(p) else "stale"
    applied_at = None
    if os.path.isfile(LAST_APPLIED_FILE):
        try:
            with open(LAST_APPLIED_FILE, "r", encoding="utf-8") as f:
                rec = json.load(f)
            applied_at = rec.get("time")
        except (json.JSONDecodeError, OSError):
            pass
    if applied_at:
        status["appliedAtMs"] = int(applied_at) * 1000
    return status


def print_current(status=None):
    """`mcode-theme current` 友好输出（含状态判定）。"""
    import datetime
    if status is None:
        status = current_status()
    if not status["applied"]:
        print("未应用: 官方默认主题（未配置 mcode-theme）")
        print("  运行 mcode-theme apply <name> 开始定制主题")
        return
    print(f"当前主题: {status['name']}")
    if status["appliedAtMs"]:
        ts = datetime.datetime.fromtimestamp(status["appliedAtMs"] / 1000)
        print(f"  应用时间: {ts:%Y-%m-%d %H:%M}")
    else:
        print("  应用时间: 未知")
    if status["state"] == "ok":
        print("  状态: 生效（原生主题，mcode 已识别）")
    else:
        print(f"  状态: 需重新 apply（主题文件缺失，运行 mcode-theme apply {status['name']}）")
    print(f"  主题文件: {SETTINGS_FILE}")


def set_plan(name):
    """Plan 模式主题。

    mcode >= 0.7.0 的原生主题机制没有 plan 模式钩子（不再改写 cli.js），
    这里退化为设置外观覆盖：<id>/dark 或 <id>/light。
    """
    tid = selected_theme_id()
    base = tid.split("/")[0] if tid else name
    p = find_theme_file(name)
    if not p:
        err(f"theme '{name}' not found in {THEME_DIR} or {LIB_DIR}")
    theme = load_theme(p)
    app = theme.get("appearance", "dark")
    _write_settings({"theme": "%s/%s" % (base, app)})
    print(f"plan mode theme set to '{name}'（原生机制：外观覆盖 {base}/{app}）")


def unset_plan():
    tid = selected_theme_id()
    if not tid:
        err("no theme selected")
    base = tid.split("/")[0]
    _write_settings({"theme": base})
    print("plan mode theme cleared.")


def random_theme():
    """随机应用一个已安装主题"""
    import secrets   # CWE-330 整改：弃用 random，改用密码学随机
    if not os.path.isdir(THEME_DIR):
        err("no themes installed.")
    names = sorted(fn[:-5] for fn in os.listdir(THEME_DIR)
                   if fn.endswith(".json") and not fn.startswith("."))
    if not names:
        err("no themes installed.")
    cur = current()
    pick = secrets.choice(names)
    # 避免选到当前主题（如果有多个）
    if len(names) > 1 and cur and cur.get("name") in names:
        others = [n for n in names if n != cur["name"]]
        pick = secrets.choice(others)
    apply(pick)
    print(f"random theme: {pick}")


def create_template(name):
    os.makedirs(THEME_DIR, exist_ok=True)
    name = sanitize_theme_name(name)
    template = {
        "name": name,
        "appearance": "dark",
        "colors": DEFAULT_UI["dark"],
        "ansi": DEFAULT_ANSI["dark"],
        "syntax": DEFAULT_SYNTAX["dark"],
    }
    os.makedirs(LIB_DIR, exist_ok=True)
    path = os.path.join(LIB_DIR, f"{name}.json")
    with safe_write_open(path, LIB_DIR, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)
    print(f"template created: {path}")
    print("edit colors then run: mcode-theme install <path>")




def list_theme_names():
    """已安装（原生目录）+ 主题库 的并集。"""
    return sorted(set(native_theme_names()) | set(lib_theme_names()))


def theme_path(name):
    """原生主题文件路径。"""
    return os.path.join(THEME_DIR, f"{name}.json")


def lib_theme_path(name):
    """主题库（可编辑源格式）路径。"""
    return os.path.join(LIB_DIR, f"{name}.json")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd not in ("restore", "update"):
        check_stale()
    try:
        return _dispatch(argv, cmd)
    except PatchAbort as e:
        err(str(e))


def _dispatch(argv, cmd):
    if cmd == "install":
        if len(argv) < 3:
            err("usage: mcode-theme install <theme.json|URL>")
        install_from_source(argv[2])
    elif cmd == "apply":
        if len(argv) < 3:
            err("usage: mcode-theme apply <name>")
        # 入口清洗：主题名不得含路径分隔符/穿越
        apply(sanitize_theme_name(argv[2]))
    elif cmd == "update":
        update_check()
    elif cmd == "plan":
        if len(argv) < 3:
            # 无参数：交互式从列表选择
            if not os.path.isdir(THEME_DIR):
                err("no themes installed. Run 'mcode-theme install <theme.json>' first.")
            names = sorted(fn[:-5] for fn in os.listdir(THEME_DIR)
                           if fn.endswith(".json") and not fn.startswith("."))
            if not names:
                err("no themes installed.")
            print("选择 plan 模式使用的主题:")
            for i, n in enumerate(names, 1):
                print(f"  {i}. {n}")
            try:
                sel = input("输入编号: ").strip()
                idx = int(sel) - 1
                if idx < 0 or idx >= len(names):
                    err("invalid selection")
            except (ValueError, EOFError):
                err("invalid input")
            set_plan(names[idx])
        else:
            # 入口清洗：主题名不得含路径分隔符/穿越
            set_plan(sanitize_theme_name(argv[2]))
    elif cmd == "unplan":
        unset_plan()
    elif cmd == "random":
        random_theme()
    elif cmd == "web":
        # Web 可视化配置器
        tool_dir = os.path.dirname(os.path.abspath(__file__))
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(tool_dir, "web.py"),               # 与工具同目录
            os.path.join(os.path.dirname(tool_dir), "mcode-themes", "web.py"),  # ~/mcode-themes/
            os.path.join(home, "mcode-themes", "web.py"),   # ~/mcode-themes/
            os.path.join(tool_dir, "scripts", "web.py"),    # 插件包布局
        ]
        web_path = next((p for p in candidates if os.path.isfile(p)), None)
        if not web_path:
            err("web.py not found; run from mcode-themes source directory")
        web_args = [sys.executable, web_path]
        if len(argv) > 2:
            web_args += argv[2:]
        os.execvp(web_args[0], web_args)
    elif cmd == "list":
        list_themes()
    elif cmd == "restore":
        restore()
    elif cmd == "current":
        if "--json" in argv[2:]:
            # --json：原始 JSON 输出（向后兼容）
            cur = current()
            print(json.dumps(cur, indent=2) if cur else "official default theme")
        else:
            print_current()
    elif cmd == "create":
        name = argv[2] if len(argv) > 2 else "my-theme"
        create_template(sanitize_theme_name(name))
    else:
        print(f"unknown command: {cmd}")
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
