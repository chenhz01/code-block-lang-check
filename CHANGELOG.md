# Changelog

All notable changes to this project are documented here.
Format based on Keep a Changelog; versioning: SemVer.

## [0.1.1] - 2026-10-13

### Fixed / Revised (round-2 iteration)
- wired --aliases extra mapping through scan_text/canonical (previously loaded but unused - found by A23)
- strip UTF-8 BOM before fence scanning (C05)
- documented nested-fence behaviour (content inside an open fence is never re-scanned) with a dedicated case C09

### Verification
- self_test re-run green after revisions: SUMMARY: PASS 64/64 (62 cases + 2 meta; >=60 gate met)
- CLI error contract re-verified (exit 0/1/2); four scaffold-v2 defenses inherited.

## [0.1.0] - 2026-10-13

### Added
- Core module `code_block_lang_check.py`: check (files/dirs, --fail-on, --aliases, --json), pure standard library.
- argparse CLI with `--json` machine output and 0/1/2 exit-code contract.
- `self_test.py` inheriting scaffold-v2 defenses: SystemExit capture, unicode-safe
  regexes, `newline=""` fixtures, and the `SUMMARY: PASS n/n` last-line contract.
- README (Performance section with [Measured] numbers and in-repo repro commands),
  MIT LICENSE, ALIGNMENT.md (16-item rubric).
