#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code-block-lang-check — lint fenced code block language annotations in Markdown.

Detects missing / unknown / non-canonical / inconsistent fence info strings
plus unclosed fences and code-looking blocks without a language. Pure stdlib.
"""
import argparse
import json
import os
import re
import sys


class LintError(Exception):
    """Recoverable input error surfaced as exit 2."""


FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
INFO_LANG_RE = re.compile(r"^[^\W\d][\w+\-.#]*", re.UNICODE)

# common alias -> canonical
ALIASES = {
    "js": "javascript", "node": "javascript", "mjs": "javascript",
    "py": "python", "python3": "python",
    "rb": "ruby",
    "sh": "shell", "bash": "shell", "zsh": "shell", "console": "shell",
    "yml": "yaml",
    "md": "markdown",
    "golang": "go",
    "c++": "cpp", "cxx": "cpp",
    "cs": "csharp", "c#": "csharp",
    "ts": "typescript",
    "ps": "powershell", "ps1": "powershell",
    "objc": "objective-c",
}

KNOWN = {
    "python", "javascript", "typescript", "json", "yaml", "html", "css",
    "shell", "sql", "c", "cpp", "csharp", "go", "java", "rust", "ruby",
    "php", "markdown", "text", "diff", "toml", "ini", "makefile",
    "dockerfile", "kotlin", "swift", "scala", "haskell", "lua", "perl",
    "r", "matlab", "xml", "powershell", "plaintext", "regex", "vim",
}

CODEISH_RE = re.compile(
    r"(^\s*(def |class |import |from |function |const |let |var |return |if |for )"
    r"|;\s*$|[{};]\s*$|=\s*\S)", re.MULTILINE)

SEVERITY_ORDER = {"info": 0, "warn": 1, "error": 2}


def canonical(lang, aliases=None):
    table = aliases if aliases is not None else ALIASES
    lang = lang.lower()
    if lang in table:
        return table[lang]
    return lang if lang in KNOWN else None


def parse_info(info):
    """First token of a fence info string, or ('', 'whitespace') variants."""
    stripped = info.strip()
    if not info:
        return "", "empty"
    if not stripped:
        return "", "whitespace"
    m = INFO_LANG_RE.match(stripped)
    if not m:
        return "", "unparseable"
    return m.group(0), "ok"


def scan_text(text, aliases=None):
    """Scan markdown text; returns list of finding dicts with 1-based line numbers."""
    if text.startswith("\ufeff"):
        text = text[1:]
    findings = []
    lines = text.splitlines()
    open_fence = None  # (char, min_len, line_no, info)
    seen_canon = {}    # canonical -> set of raw tags
    in_fence = False
    fence_char = ""
    fence_len = 0
    fence_start = 0
    fence_lang_raw = ""
    fence_canon = None
    body_lines = []

    for idx, line in enumerate(lines, 1):
        m = FENCE_RE.match(line)
        if not in_fence and m:
            indent, marker, info = m.group(1), m.group(2), m.group(3)
            fence_char, fence_len = marker[0], len(marker)
            raw, status = parse_info(info)
            fence_start = idx
            fence_lang_raw = raw
            body_lines = []
            if status == "empty":
                findings.append(dict(line=idx, code="L001", severity="warn",
                                     message="fenced block has no language annotation"))
                fence_canon = None
            elif status == "whitespace":
                findings.append(dict(line=idx, code="L005", severity="info",
                                     message="fence info string is whitespace only"))
                fence_canon = None
            elif status == "unparseable":
                findings.append(dict(line=idx, code="L002", severity="warn",
                                     message="unparseable fence info string %r" % info.strip()))
                fence_canon = None
            else:
                low = raw.lower()
                canon = canonical(low, aliases)
                if canon is None:
                    findings.append(dict(line=idx, code="L002", severity="warn",
                                         message="unknown language %r" % raw))
                    fence_canon = low
                else:
                    fence_canon = canon
                    if low != canon:
                        findings.append(dict(line=idx, code="L003", severity="info",
                                             message="alias %r -> canonical %r" % (low, canon)))
                    seen_canon.setdefault(canon, set()).add(low)
            in_fence = True
            continue
        if in_fence:
            m = FENCE_RE.match(line)
            if m and m.group(2)[0] == fence_char and len(m.group(2)) >= fence_len \
                    and not m.group(3).strip():
                # closing fence
                if fence_canon is None and CODEISH_RE.search("\n".join(body_lines)):
                    findings.append(dict(
                        line=fence_start, code="L007", severity="warn",
                        message="code-looking block opened without language (body matches code heuristics)"))
                in_fence = False
            else:
                body_lines.append(line)

    if in_fence:
        findings.append(dict(line=fence_start, code="L006", severity="warn",
                             message="unclosed fence opened at line %d" % fence_start))

    for canon, tags in sorted(seen_canon.items()):
        if len(tags) > 1:
            findings.append(dict(line=0, code="L004", severity="info",
                                 message="inconsistent aliases for %s: %s"
                                         % (canon, ", ".join(sorted(tags)))))
    return findings


def collect_files(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for f in sorted(files):
                    if f.lower().endswith((".md", ".markdown")):
                        out.append(os.path.join(root, f))
        else:
            out.append(p)
    return out


def check_paths(paths, extra_aliases=None):
    aliases = dict(ALIASES)
    if extra_aliases:
        aliases.update(extra_aliases)
    all_findings = {}
    for path in collect_files(paths):
        try:
            with open(path, "r", encoding="utf-8", newline="") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            all_findings[path] = [dict(line=0, code="L098", severity="error",
                                       message="unreadable: %s" % exc)]
            continue
        all_findings[path] = scan_text(text, aliases=aliases)
    return all_findings


def summarize(findings_by_file, threshold):
    order = SEVERITY_ORDER[threshold]
    total = 0
    by_sev = {"info": 0, "warn": 0, "error": 0}
    for _f, items in findings_by_file.items():
        for it in items:
            by_sev[it["severity"]] = by_sev.get(it["severity"], 0) + 1
            total += 1
    blocking = sum(v for k, v in by_sev.items() if SEVERITY_ORDER[k] >= order)
    return {"total": total, "by_severity": by_sev, "blocking": blocking}


def _cmd_check(args):
    extra = None
    if args.aliases:
        try:
            with open(args.aliases, "r", encoding="utf-8") as fh:
                extra = json.load(fh)
            if not isinstance(extra, dict):
                raise LintError("aliases file must be a JSON object")
        except (OSError, json.JSONDecodeError) as exc:
            raise LintError("cannot load aliases: %s" % exc)
    findings = check_paths(args.paths, extra_aliases=extra)
    summary = summarize(findings, args.fail_on)
    if args.json:
        print(json.dumps({"files": findings, "summary": summary}, ensure_ascii=False, indent=2))
    else:
        for path in sorted(findings):
            for it in findings[path]:
                loc = "line %d" % it["line"] if it["line"] else "-"
                print("%s:%s: %s [%s] %s" % (path, loc, it["code"], it["severity"], it["message"]))
        print("summary: %d finding(s) %s" % (summary["total"], summary["by_severity"]))
    return 1 if summary["blocking"] > 0 else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="code-block-lang-check",
        description="Check Markdown fenced code blocks for missing/unknown/"
                    "inconsistent language annotations.")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("check", help="check markdown files or directories")
    p.add_argument("paths", nargs="+", help=".md files or directories")
    p.add_argument("--aliases", help="JSON file mapping extra alias -> canonical")
    p.add_argument("--fail-on", choices=("info", "warn", "error"), default="warn")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd != "check":
        parser.print_help()
        return 2
    try:
        return _cmd_check(args)
    except LintError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
