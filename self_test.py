# -*- coding: utf-8 -*-
"""self_test for code-block-lang-check — inherits scaffold-v2 defenses D1-D4."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")  # D3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import code_block_lang_check as mod  # noqa: E402


def run_cli(argv):  # D1
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = mod.main(argv)
            code = 0 if rc is None else rc
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


CASES = []


def case(name, cat):
    def deco(fn):
        CASES.append((name, cat, fn))
        return fn
    return deco


TMP = tempfile.mkdtemp(prefix="cblc_selftest_")


def write_md(name, text):
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8", newline="") as fh:  # D3
        fh.write(text)
    return p


def codes(path):
    return [f["code"] for f in mod.scan_text(open(path, encoding="utf-8").read())]


MD = "# t\n```python\nx = 1\n```\n"

# ------------------------------------------------------------------ [A] functional

@case("A01_clean_file_no_findings", "A")
def t():
    p = write_md("a01.md", MD)
    assert codes(p) == []

@case("A02_missing_lang_L001", "A")
def t():
    p = write_md("a02.md", "```\nx = 1\n```\n")
    assert "L001" in codes(p)

@case("A03_unknown_lang_L002", "A")
def t():
    p = write_md("a03.md", "```klingon\nx\n```\n")
    assert "L002" in codes(p)

@case("A04_alias_L003_js", "A")
def t():
    p = write_md("a04.md", "```js\nvar x\n```\n")
    assert "L003" in codes(p)

@case("A05_inconsistent_alias_L004", "A")
def t():
    p = write_md("a05.md", "```js\na\n```\n```javascript\nb\n```\n")
    assert "L004" in codes(p)

@case("A06_whitespace_info_L005", "A")
def t():
    p = write_md("a06.md", "``` \nx\n```\n")
    assert "L005" in codes(p)

@case("A07_unclosed_fence_L006", "A")
def t():
    p = write_md("a07.md", "```python\nx = 1\n")
    assert "L006" in codes(p)

@case("A08_codeish_no_lang_L007", "A")
def t():
    p = write_md("a08.md", "```\ndef f():\n    return 1\n```\n")
    assert "L007" in codes(p)

@case("A09_canonical_js_detection", "A")
def t():
    assert mod.canonical("js") == "javascript"

@case("A10_canonical_unknown_none", "A")
def t():
    assert mod.canonical("klingon") is None

@case("A11_canonical_known_identity", "A")
def t():
    assert mod.canonical("Python") == "python"

@case("A12_alias_bash_to_shell", "A")
def t():
    assert mod.canonical("bash") == "shell"

@case("A13_tilde_fence_supported", "A")
def t():
    p = write_md("a13.md", "~~~python\nx\n~~~\n")
    assert codes(p) == []

@case("A14_four_backtick_fence", "A")
def t():
    p = write_md("a14.md", "````python\n```\n````\n")
    assert codes(p) == []

@case("A15_cli_check_clean_exit0", "A")
def t():
    p = write_md("a15.md", MD)
    code, out, _ = run_cli(["check", p])
    assert code == 0 and "summary" in out

@case("A16_cli_check_finding_exit1", "A")
def t():
    p = write_md("a16.md", "```\nx\n```\n")
    code, out, _ = run_cli(["check", p])
    assert code == 1 and "L001" in out

@case("A17_cli_json_mode", "A")
def t():
    p = write_md("a17.md", "```\nx\n```\n")
    code, out, _ = run_cli(["check", p, "--json"])
    assert code == 1
    data = json.loads(out)
    assert data["summary"]["total"] >= 1 and p in data["files"]

@case("A18_fail_on_info_exit1", "A")
def t():
    p = write_md("a18.md", "```js\na\n```\n")
    code, _, _ = run_cli(["check", p, "--fail-on", "info"])
    assert code == 1

@case("A19_fail_on_error_ignores_warn", "A")
def t():
    p = write_md("a19.md", "```\nx\n```\n")
    code, _, _ = run_cli(["check", p, "--fail-on", "error"])
    assert code == 0

@case("A20_line_numbers_accurate", "A")
def t():
    p = write_md("a20.md", "line1\nline2\n```\nx\n```\n")
    f = mod.scan_text(open(p, encoding="utf-8").read())
    assert f[0]["line"] == 3

@case("A21_collect_files_recursive", "A")
def t():
    d = os.path.join(TMP, "sub_dir")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "n.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write(MD)
    files = mod.collect_files([d])
    assert len(files) == 1 and files[0].endswith("n.md")

@case("A22_severity_summary_counts", "A")
def t():
    s = mod.summarize({"f": [dict(line=1, code="L001", severity="warn", message="m"),
                             dict(line=2, code="L003", severity="info", message="m")]}, "warn")
    assert s["total"] == 2 and s["blocking"] == 1

@case("A23_alias_file_extra_mapping", "A")
def t():
    ap = os.path.join(TMP, "alias.json")
    with open(ap, "w", encoding="utf-8", newline="") as fh:
        json.dump({"zig": "ziglang"}, fh)
    p = write_md("a23.md", "```zig\nx\n```\n")
    code, out, _ = run_cli(["check", p, "--aliases", ap, "--json"])
    assert code == 0

@case("A24_extra_alias_unmapped_still_unknown", "A")
def t():
    p = write_md("a24.md", "```fortran77\nx\n```\n")
    assert "L002" in codes(p)

# ------------------------------------------------------------------ [B] exception / CLI contract

@case("B01_cli_no_subcommand_exit2", "B")
def t():
    assert run_cli([])[0] == 2

@case("B02_cli_unknown_subcommand_exit2", "B")
def t():
    assert run_cli(["lint", "x.md"])[0] == 2

@case("B03_missing_path_read_error", "B")
def t():
    code, out, _ = run_cli(["check", os.path.join(TMP, "ghost.md"), "--json"])
    assert code == 1 and "L098" in out

@case("B04_bad_fail_on_value", "B")
def t():
    assert run_cli(["check", "x.md", "--fail-on", "fatal"])[0] == 2

@case("B05_aliases_bad_json_exit2", "B")
def t():
    ap = write_md("bad_alias.json", "{oops")
    code, _, err = run_cli(["check", "x.md", "--aliases", ap])
    assert code == 2 and "error" in err

@case("B06_aliases_not_object_exit2", "B")
def t():
    ap = write_md("arr_alias.json", "[1,2]")
    code, _, _ = run_cli(["check", "x.md", "--aliases", ap])
    assert code == 2

@case("B07_aliases_missing_file_exit2", "B")
def t():
    code, _, _ = run_cli(["check", "x.md", "--aliases", os.path.join(TMP, "ghost.json")])
    assert code == 2

@case("B08_empty_path_list_usage_error", "B")
def t():
    assert run_cli(["check"])[0] == 2

@case("B09_scan_unicode_lang_tag", "B")
def t():
    f = mod.scan_text("```日本語\nx\n```\n")
    assert f and f[0]["code"] == "L002"

@case("B10_scan_emoji_body", "B")
def t():
    assert mod.scan_text("```python\nprint('🚀🔥')\n```\n") == []

@case("B11_json_mode_structure_keys", "B")
def t():
    p = write_md("b11.md", "```\nx\n```\n")
    code, out, _ = run_cli(["check", p, "--json"])
    data = json.loads(out)
    assert set(data) == {"files", "summary"}

@case("B12_info_str_with_title_uses_first_token", "B")
def t():
    f = mod.scan_text("```python title=main\nx\n```\n")
    assert f == []

@case("B13_lint_error_severity_blocks", "B")
def t():
    s = mod.summarize({"f": [dict(line=1, code="L099", severity="error", message="m")]}, "warn")
    assert s["blocking"] == 1

@case("B14_check_directory_aggregates", "B")
def t():
    d = os.path.join(TMP, "b14_dir")
    os.makedirs(d, exist_ok=True)
    for n in ("1.md", "2.md"):
        with open(os.path.join(d, n), "w", encoding="utf-8", newline="") as fh:
            fh.write("```\nx\n```\n")
    code, out, _ = run_cli(["check", d, "--json"])
    assert code == 1 and len(json.loads(out)["files"]) == 2

@case("B15_non_markdown_in_dir_ignored", "B")
def t():
    d = os.path.join(TMP, "b15_dir")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "x.txt"), "w", encoding="utf-8", newline="") as fh:
        fh.write("```\n```\n")
    code, out, _ = run_cli(["check", d, "--json"])
    assert code == 0 and json.loads(out)["summary"]["total"] == 0

@case("B16_info_string_unparseable", "B")
def t():
    f = mod.scan_text("```!!!\nx\n```\n")
    assert f[0]["code"] == "L002"

@case("B17_exit0_when_only_info_default", "B")
def t():
    p = write_md("b17.md", "```js\na\n```\n")
    assert run_cli(["check", p])[0] == 0

@case("B18_help_flag_exit0", "B")
def t():
    code, out, _ = run_cli(["--help"])
    assert code == 0 and "fenced" in out

# ------------------------------------------------------------------ [C] extreme edge

@case("C01_empty_file_clean", "C")
def t():
    p = write_md("c01.md", "")
    assert codes(p) == []

@case("C02_only_text_no_fences", "C")
def t():
    p = write_md("c02.md", "plain text\nnothing here\n")
    assert codes(p) == []

@case("C03_crlf_line_endings", "C")
def t():
    p = write_md("c03.md", "```\r\nx\r\n```\r\n")
    assert "L001" in codes(p)

@case("C04_no_trailing_newline", "C")
def t():
    p = write_md("c04.md", "```python\nx = 1\n```")
    assert codes(p) == []

@case("C05_bom_prefix_file", "C")
def t():
    p = write_md("c05.md", "﻿```python\nx\n```\n")
    assert codes(p) == []

@case("C06_indented_fence_under_4_spaces", "C")
def t():
    p = write_md("c06.md", "  ```python\nx\n  ```\n")
    assert codes(p) == []

@case("C07_indented_4spaces_not_fence", "C")
def t():
    p = write_md("c07.md", "    ```python\nx\n    ```\n")
    assert codes(p) == []

@case("C08_mismatched_fence_chars", "C")
def t():
    p = write_md("c08.md", "```python\nx\n~~~\n")
    assert "L006" in codes(p)

@case("C09_nested_triplet_inside_quad", "C")
def t():
    # documented behaviour: content inside an open fence is never re-scanned,
    # so a ``` triplet inside a ```` block produces no findings
    p = write_md("c09.md", "````markdown\n```js\n```\n````\n")
    assert codes(p) == []

@case("C10_unclosed_then_reopen", "C")
def t():
    p = write_md("c10.md", "```python\nx\n```\n```\ny\n")
    fs = codes(p)
    assert "L001" in fs and "L006" in fs

@case("C11_closing_fence_with_lang_ignored", "C")
def t():
    f = mod.scan_text("```python\nx\n``` not-a-close\ny\n")
    assert any(x["code"] == "L006" for x in f)

@case("C12_huge_file_scan_speed", "C")
def t():
    text = MD * 5000
    import time
    t0 = __import__("time").perf_counter()
    f = mod.scan_text(text)
    assert __import__("time").perf_counter() - t0 < 5 and f == []

@case("C13_many_aliases_consistency", "C")
def t():
    p = write_md("c13.md", "```js\na\n```\n```node\nb\n```\n```mjs\nc\n```\n")
    fs = codes(p)
    assert "L004" in fs

@case("C14_long_info_string", "C")
def t():
    p = write_md("c14.md", "```python " + "x" * 500 + "\ny\n```\n")
    assert codes(p) == []

@case("C15_cjk_content_lines", "C")
def t():
    p = write_md("c15.md", "```python\nprint('你好世界')\n```\n")
    assert codes(p) == []

@case("C16_control_chars_body", "C")
def t():
    p = write_md("c16.md", "```python\nx = '\x07'\n```\n")
    assert codes(p) == []

@case("C17_empty_info_after_lang_spaces", "C")
def t():
    p = write_md("c17.md", "```\t\nx\n```\n")
    assert "L005" in codes(p)

@case("C18_uppercase_lang_normalized", "C")
def t():
    f = mod.scan_text("```PYTHON\nx\n```\n")
    assert f == []

@case("C19_dir_with_mixed_severities_json", "C")
def t():
    d = os.path.join(TMP, "c19_dir")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "a.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("```js\na\n```\n")
    with open(os.path.join(d, "b.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("```\nb\n```\n")
    code, out, _ = run_cli(["check", d, "--json"])
    data = json.loads(out)
    assert data["summary"]["by_severity"]["warn"] >= 1
    assert data["summary"]["by_severity"]["info"] >= 1

@case("C20_crlf_json_mode_line_numbers", "C")
def t():
    p = write_md("c20.md", "one\r\ntwo\r\n```\r\nx\r\n```\r\n")
    code, out, _ = run_cli(["check", p, "--json"])
    assert json.loads(out)["files"][p][0]["line"] == 3


class TestAll(unittest.TestCase):
    pass


def _build():
    for i, (name, cat, fn) in enumerate(CASES):
        def make(f):
            def m(self):
                f()
            return m
        slug = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in name)
        setattr(TestAll, "test_%s_%03d_%s" % (cat, i, slug), make(fn))
_build()


class TestMeta(unittest.TestCase):
    def test_case_count_ge_60(self):
        self.assertGreaterEqual(len(CASES), 60)

    def test_categories_present(self):
        self.assertEqual({c for _, c, _ in CASES}, {"A", "B", "C"})


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))  # D4
    sys.exit(0 if fails == 0 else 1)
