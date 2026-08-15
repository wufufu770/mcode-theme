#!/usr/bin/env python3
"""
mcode-theme Web GUI - MiniMax Code CLI 主题可视化配置器

启动:  mcode-theme web [--port 8598]
访问:  http://localhost:8598

功能:
  - 模块化调色盘（UI 配色 / ANSI / 语法高亮 / Logo / 字体 / Plan 主题）
  - 实时预览（模拟 mcode 界面，改动即时显示）
  - 一键应用（写回 cli.js）/ 保存主题 / 恢复官方
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# ---- 复用 mcode-theme 的路径与函数 ----
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOL_DIR)

import mcode_theme_lib  # noqa: E402  (由 mcode-theme 生成或同目录)

HERE = os.path.dirname(os.path.abspath(__file__))
# 兼容两种布局: web.py 同目录 web/index.html, 或 scripts/ 上一级 web/index.html
INDEX_PATH = os.path.join(HERE, "web", "index.html")
if not os.path.isfile(INDEX_PATH):
    parent = os.path.dirname(HERE)
    candidate = os.path.join(parent, "web", "index.html")
    if os.path.isfile(candidate):
        INDEX_PATH = candidate

UI_KEYS = mcode_theme_lib.UI_KEYS
SYNTAX_KEYS = mcode_theme_lib.SYNTAX_KEYS
ANSI_KEYS = [k for k in mcode_theme_lib.UI_KEYS if k != "userMessageBg"]

FONT_STACKS = [
    {"name": "JetBrains Mono", "stack": "'JetBrains Mono', 'Fira Code', Consolas, monospace"},
    {"name": "Fira Code", "stack": "'Fira Code', 'JetBrains Mono', Consolas, monospace"},
    {"name": "Cascadia Code", "stack": "'Cascadia Code', 'JetBrains Mono', Consolas, monospace"},
    {"name": "Source Code Pro", "stack": "'Source Code Pro', Consolas, monospace"},
    {"name": "Ubuntu Mono", "stack": "'Ubuntu Mono', Consolas, monospace"},
    {"name": "DejaVu Sans Mono", "stack": "'DejaVu Sans Mono', Consolas, monospace"},
    {"name": "Noto Sans Mono", "stack": "'Noto Sans Mono', Consolas, monospace"},
    {"name": "系统默认等宽", "stack": "ui-monospace, 'Cascadia Code', Consolas, monospace"},
]


class ThemeServer(BaseHTTPRequestHandler):
    server_version = "mcode-theme/1.0"
    # 允许立即重用端口（避免 Ctrl+C 后 TIME_WAIT 短暂占用）
    allow_reuse_address = True

    # ---------- helpers ----------
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _ok(self, obj):
        self._send(200, obj)

    def _err(self, msg, code=400):
        self._send(code, {"error": str(msg)})

    # ---------- API ----------
    def _api_state(self):
        cur = mcode_theme_lib.current() or {}
        return {
            "themes": mcode_theme_lib.list_theme_names(),
            "current": cur.get("name"),
            "currentTheme": cur,
            "planTheme": cur.get("planTheme"),
            "defaults": {
                "ui": mcode_theme_lib.DEFAULT_UI,
                "ansi": mcode_theme_lib.DEFAULT_ANSI,
                "syntax": mcode_theme_lib.DEFAULT_SYNTAX,
            },
            "uiKeys": UI_KEYS,
            "syntaxKeys": SYNTAX_KEYS,
            "ansiKeys": ANSI_KEYS,
            "fonts": FONT_STACKS,
            "version": mcode_theme_lib.cli_fingerprint().get("version"),
        }

    def _api_theme(self, name):
        path = mcode_theme_lib.theme_path(name)
        if not os.path.isfile(path):
            self._err(f"theme '{name}' not found")
            return
        with open(path, "r", encoding="utf-8") as f:
            theme = json.load(f)
        # 补全默认键，前端好渲染
        app = theme.get("appearance", "dark")
        full = {
            "name": theme.get("name", name),
            "appearance": app,
            "colors": {**mcode_theme_lib.DEFAULT_UI[app], **theme.get("colors", {})},
            "ansi": {**mcode_theme_lib.DEFAULT_ANSI[app], **theme.get("ansi", {})},
            "syntax": {**mcode_theme_lib.DEFAULT_SYNTAX[app], **theme.get("syntax", {})},
            "logo": theme.get("logo", theme.get("colors", {}).get("brand")),
        }
        self._ok(full)

    def _api_apply(self, payload):
        theme = payload.get("theme")
        if not isinstance(theme, dict) or "colors" not in theme:
            self._err("missing theme.colors")
            return
        name = theme.get("name") or "live-edit"
        appearance = theme.get("appearance", "dark")
        tmp = os.path.join(mcode_theme_lib.THEME_DIR, f".live-{os.getpid()}.json")
        os.makedirs(mcode_theme_lib.THEME_DIR, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(theme, f, ensure_ascii=False)
        try:
            parsed = mcode_theme_lib.load_theme(tmp)
        except Exception as e:
            os.remove(tmp)
            self._err(f"主题校验失败: {e}")
            return
        os.remove(tmp)
        try:
            mcode_theme_lib.patch_cli(parsed)
        except Exception as e:
            self._err(f"应用失败: {e}")
            return
        self._ok({"ok": True, "name": parsed["name"], "appearance": appearance})

    def _api_save(self, payload):
        name = payload.get("name")
        theme = payload.get("theme")
        if not name or not isinstance(theme, dict) or "colors" not in theme:
            self._err("missing name or theme.colors")
            return
        theme["name"] = name
        path = mcode_theme_lib.theme_path(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(theme, f, ensure_ascii=False, indent=2)
        self._ok({"ok": True, "saved": name})

    def _api_plan(self, payload):
        name = payload.get("name")
        try:
            if name:
                mcode_theme_lib.set_plan(name)
            else:
                mcode_theme_lib.unset_plan()
        except Exception as e:
            self._err(f"设置 Plan 主题失败: {e}")
            return
        self._ok({"ok": True, "planTheme": name or None})

    def _api_restore(self):
        try:
            mcode_theme_lib.restore()
        except Exception as e:
            self._err(f"恢复失败: {e}")
            return
        self._ok({"ok": True})

    def _api_delete(self, payload):
        name = payload.get("name")
        if not name:
            self._err("missing name")
            return
        try:
            path = mcode_theme_lib.theme_path(name)
            if os.path.isfile(path):
                os.remove(path)
            cur = mcode_theme_lib.current()
            if cur and cur.get("name") == name:
                mcode_theme_lib.restore()
        except Exception as e:
            self._err(f"删除失败: {e}")
            return
        self._ok({"ok": True})

    # ---------- routing ----------
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            if os.path.isfile(INDEX_PATH):
                with open(INDEX_PATH, "rb") as f:
                    self._send(200, f.read(), "text/html")
            else:
                self._err("web/index.html not found; run from plugin directory", 500)
            return
        if url.path == "/api/state":
            return self._ok(self._api_state())
        m = re.match(r"^/api/theme/([^/]+)$", url.path)
        if m:
            return self._api_theme(m.group(1))
        self._err("not found", 404)

    def do_POST(self):
        url = urlparse(self.path)
        payload = self._read_json()
        if url.path == "/api/apply":
            return self._api_apply(payload)
        if url.path == "/api/save":
            return self._api_save(payload)
        if url.path == "/api/plan":
            return self._api_plan(payload)
        if url.path == "/api/restore":
            return self._api_restore()
        if url.path == "/api/delete":
            return self._api_delete(payload)
        self._err("not found", 404)

    def log_message(self, fmt, *args):
        sys.stderr.write("[mcode-theme] %s\n" % (fmt % args))


def main():
    port = 8598
    host = "127.0.0.1"
    if "--port" in sys.argv:
        i = sys.argv.index("--port")
        if i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    if "--host" in sys.argv:
        i = sys.argv.index("--host")
        host = sys.argv[i + 1] if i + 1 < len(sys.argv) else "127.0.0.1"

    if not os.path.isfile(INDEX_PATH):
        print(f"error: {INDEX_PATH} not found", file=sys.stderr)
        sys.exit(1)

    # 端口占用检测：给出友好提示
    if port > 0:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            probe.settimeout(1)
            probe.bind((host, port))
            probe.close()
        except OSError:
            print(f"error: 端口 {port} 已被占用。", file=sys.stderr)
            print(f"  可能原因：之前启动的 web 服务没有退出。", file=sys.stderr)
            print(f"  解决方法：", file=sys.stderr)
            print(f"    1. 查找占用进程:  ss -ltnp | grep {port}", file=sys.stderr)
            print(f"    2. 结束旧进程:    pkill -f web.py", file=sys.stderr)
            print(f"    3. 或换个端口:    mcode-theme web --port {port + 1}", file=sys.stderr)
            sys.exit(1)

    httpd = ThreadingHTTPServer((host, port), ThemeServer)
    actual_port = httpd.server_address[1]
    if port == 0:
        port = actual_port
    print("=" * 60)
    print("  MiniMax Code 主题可视化配置器")
    print(f"  打开浏览器访问:  http://{host}:{port}")
    print("  关闭: 在本窗口按 Ctrl+C")
    print("  提示: 端口被占用时用 `mcode-theme web --port <新端口>`")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
        httpd.shutdown()


if __name__ == "__main__":
    main()
