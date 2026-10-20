"""Keine Platzhaltertexte im Repository (Gesamtpaket 7.6)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [r"Lorem", r"TODO", r"\bxxx\b", r"\bBeispiel\b"]
SKIP_DIRS = {
    ".git",
    ".venv",
    "data",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".hypothesis",
    ".nicegui",
}
# Diese Dateien nennen die verbotenen Wörter als Regel.
SKIP_FILES = {"docs/Gesamtpaket.md", "CLAUDE.md", "tests/test_no_placeholders.py"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".txt", ".json", ".css", ".html", ".js", ""}


def candidate_files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        if rel.as_posix() in SKIP_FILES or path.suffix not in TEXT_SUFFIXES:
            continue
        if path.name.endswith("LICENSE.txt"):
            continue
        out.append(path)
    return out


def test_no_placeholder_texts() -> None:
    hits = []
    for path in candidate_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PATTERNS:
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{path.relative_to(ROOT)}:{line}: {m.group(0)}")
    assert not hits, "\n".join(hits)


def test_scan_covers_sources() -> None:
    names = {p.relative_to(ROOT).as_posix() for p in candidate_files()}
    assert "src/tk/scenarios.py" in names
    assert "README.md" in names or "docs/prompt_log.md" in names
