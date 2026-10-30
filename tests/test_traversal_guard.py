#!/usr/bin/env python3
"""路径遍历 / SSRF 攻击面测试（静态反证：逐条证明候选不成立）。

## 为什么做这个
工具的 CLI 入口接受路径/主题名参数，主题 JSON 的 name 字段还会拼进文件名。
这一类「不可信片段 + 可信根目录」的拼接正是路径遍历的经典攻击面；
`install <URL>` 则是 SSRF 攻击面。光有防护实现不够——需要攻击模拟
测试把防护**证明**出来，作为候选判定的静态反证。

## 判据（四条，逐条独立）
  1. 越界写必须被拒绝 —— 不得在允许目录之外创建/写入任何文件
  2. 越界读必须被拒绝 —— 不得读取允许目录之外的文件（含符号链接逃逸）
  3. 内网 SSRF 必须被拒绝 —— file 协议 / 环回 / 私网 / 链路本地（云元数据）全失败
  4. 恶意主题名（../../x）端到端不得逃逸输出目录 —— 真跑 CLI，验副作用

用法：python3 tests/test_traversal_guard.py
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import mcode_theme_lib as m  # noqa: E402


def _run(script, *args):
    """以子进程真跑 CLI（脚本 + 参数），返回 CompletedProcess。"""
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, script), *args],
        capture_output=True, text=True, cwd=ROOT)


class TestSanitizePath(unittest.TestCase):
    """判据 1/2：sanitize_path 的拒绝语义。"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="mct-root-")
        self.outside = tempfile.mkdtemp(prefix="mct-out-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.outside, ignore_errors=True)

    def test_accept_inside_root(self):
        p = m.sanitize_path(os.path.join(self.root, "a.json"), self.root)
        self.assertTrue(p.startswith(os.path.realpath(self.root)))

    def test_reject_parent_escape(self):
        # ../ 逃逸
        with self.assertRaises(ValueError):
            m.sanitize_path(os.path.join(self.root, "..", "evil.json"), self.root)

    def test_reject_absolute_outside(self):
        with self.assertRaises(ValueError):
            m.sanitize_path(os.path.join(self.outside, "evil.json"), self.root)

    def test_reject_symlink_escape(self):
        # 判据 2 变体：root 内的符号链接指向 root 外 → realpath 解析后拒绝
        link = os.path.join(self.root, "innocent.json")
        os.symlink(os.path.join(self.outside, "target.json"), link)
        with self.assertRaises(ValueError):
            m.sanitize_path(link, self.root)


class TestSafeOpenWrappers(unittest.TestCase):
    """判据 1/2：读/写统一卡口在真实 open 前拦截。"""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="mct-wrap-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_write_wrapper_blocks_escape(self):
        with self.assertRaises(ValueError):
            with m.safe_write_open(os.path.join(self.root, "..", "evil.json"),
                                   self.root, "w") as f:
                f.write("x")
        self.assertFalse(os.path.exists(
            os.path.join(os.path.dirname(self.root), "evil.json")))

    def test_read_wrapper_blocks_escape(self):
        secret = tempfile.NamedTemporaryFile(delete=False)
        secret.write(b"secret")
        secret.close()
        try:
            with self.assertRaises(ValueError):
                with m.safe_read_open(secret.name, self.root):
                    pass
        finally:
            os.unlink(secret.name)

    def test_write_wrapper_normal_path_ok(self):
        p = os.path.join(self.root, "ok.json")
        with m.safe_write_open(p, self.root, "w", encoding="utf-8") as f:
            f.write("{}")
        with m.safe_read_open(p, self.root, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{}")


class TestThemeName(unittest.TestCase):
    """判据 1：主题名（拼文件名的不可信片段）拒绝穿越。"""

    def test_reject_traversal_names(self):
        for bad in ("../evil", "a/b", "a\\b", ".hidden", "..", "x\x00y", ""):
            with self.assertRaises(SystemExit, msg=bad):
                m.sanitize_theme_name(bad)

    def test_accept_normal_names(self):
        for ok in ("violet", "violet.light", "对音-深色", "Dracula Pro"):
            self.assertEqual(m.sanitize_theme_name(ok), ok)

    def test_native_theme_path_never_escapes_theme_dir(self):
        with self.assertRaises(SystemExit):
            m.native_theme_path("../../evil")


class TestFetchUrl(unittest.TestCase):
    """判据 3：SSRF 防护（无需出网：全部为本地可判定的拒绝用例）。"""

    def test_reject_non_http_scheme(self):
        with self.assertRaises(SystemExit):
            m.validate_fetch_url("file:///etc/passwd")

    def test_reject_loopback(self):
        for url in ("http://127.0.0.1:5003/steal", "http://localhost/admin"):
            with self.assertRaises(SystemExit, msg=url):
                m.validate_fetch_url(url)

    def test_reject_private_and_linklocal(self):
        for url in ("http://10.0.0.1/", "http://192.168.1.1/",
                    "http://169.254.169.254/latest/meta-data/",  # 云元数据
                    "http://[::1]/"):
            with self.assertRaises(SystemExit, msg=url):
                m.validate_fetch_url(url)


class TestCliEntrypoints(unittest.TestCase):
    """判据 4：恶意参数端到端攻击模拟（真跑 CLI，验副作用不存在）。"""

    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="mct-cli-")

    def tearDown(self):
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_import_pi_traversal_name_blocked(self):
        out = os.path.join(self.scratch, "out")
        evil = os.path.join(self.scratch, "evil.json")
        with pathlib.Path(evil).open("w", encoding="utf-8") as f:
            json.dump({"name": "../../../tmp/mct-evil", "colors": {}}, f)
        r = _run("import-pi.py", evil, "--out", out)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertFalse(os.path.exists("/tmp/mct-evil.json"))
        self.assertFalse(os.listdir(out) if os.path.isdir(out) else False)

    def test_import_opencode_traversal_name_blocked(self):
        out = os.path.join(self.scratch, "out")
        src = os.path.join(self.scratch, "oc.json")
        with pathlib.Path(src).open("w", encoding="utf-8") as f:
            json.dump({"$schema": "https://opencode.ai/theme.json"}, f)
        r = _run("import-opencode.py", src, "--name", "../evil", "--out", out)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.scratch, "evil.json")))

    def test_gen_light_traversal_name_skipped(self):
        # 借真实主题的结构，仅把 name 换成穿越串
        src_theme = os.path.join(ROOT, "themes", "violet.json")
        with open(src_theme, encoding="utf-8") as f:
            theme = json.load(f)
        theme["name"] = "../evil"
        d = os.path.join(self.scratch, "themes")
        os.makedirs(d)
        with pathlib.Path(d, "v.json").open("w", encoding="utf-8") as f:
            json.dump(theme, f)
        r = _run("gen-light-variants.py", d)
        self.assertFalse(os.path.exists(os.path.join(self.scratch, "evil.light.json")),
                         "穿越主题名逃逸出扫描目录")
        self.assertFalse(os.path.exists(os.path.join(d, "..", "evil.light.json")))

    def test_validate_themes_traversal_dirarg_blocked(self):
        r = _run("validate-themes.py", "../secrets")
        self.assertEqual(r.returncode, 1, r.stderr)

    def test_theme_metadata_traversal_dirarg_blocked(self):
        r = _run("theme-metadata.py", "themes/../../..")
        self.assertNotEqual(r.returncode, 0)

    def test_create_template_traversal_name_blocked(self):
        saved = m.LIB_DIR
        m.LIB_DIR = self.scratch
        try:
            with self.assertRaises(SystemExit):
                m.create_template("../../evil")
            self.assertFalse(os.path.exists(
                os.path.join(os.path.dirname(self.scratch), "evil.json")))
        finally:
            m.LIB_DIR = saved


if __name__ == "__main__":
    unittest.main(verbosity=2)
