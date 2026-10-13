#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "rich>=13.0.0"]
# ///
"""Validate note frontmatter and placement.

Checks the mechanical things a reviewer should not have to: required metadata, valid taxonomy
values, correct placement, and unrendered .qmd sources. Content review (description drift,
placeholders, alt text) is left to a human or the `review-post` style pass.

Usage:
  uv run scripts/validate-notes.py                       # all notes
  uv run scripts/validate-notes.py content/notes/x/index.md
  uv run scripts/validate-notes.py --strict              # warnings become errors
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml
from rich.console import Console

console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "content" / "notes"
TOPICS_FILE = REPO_ROOT / "data" / "topics.yaml"

REQUIRED_FIELDS = ["title", "date", "description", "topics"]
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|TBD|FIXME|XXX)\b|\[insert [^\]]*\]|lorem ipsum", re.I
)
H1_RE = re.compile(r"^#\s+\S", re.M)


def has_bare_code_fence(body: str) -> bool:
    """True if any OPENING fence lacks a language tag.

    Must track open/close state: a closing ``` is bare by definition and is not a problem.
    """
    inside = False
    for line in body.split("\n"):
        if line.startswith("```"):
            if inside:
                inside = False
            elif not line[3:].strip():
                return True
            else:
                inside = True
    return False


def split_frontmatter(text: str):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, text
    try:
        fm = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError:
        return None, text
    return fm, "\n".join(lines[end + 1 :])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    args = parser.parse_args()

    valid_topics = (
        set(yaml.safe_load(TOPICS_FILE.read_text()) or [])
        if TOPICS_FILE.exists()
        else set()
    )

    if args.paths:
        targets = [Path(p) for p in args.paths]
    else:
        targets = sorted(NOTES_DIR.glob("**/index.md")) if NOTES_DIR.exists() else []

    errors: list[str] = []
    warnings: list[str] = []

    for path in targets:
        rel = path.relative_to(REPO_ROOT) if path.is_absolute() is False else path
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        if fm is None:
            errors.append(f"{rel}: missing or unparseable frontmatter")
            continue

        for field in REQUIRED_FIELDS:
            if not fm.get(field):
                errors.append(f"{rel}: missing required field `{field}`")

        for topic in fm.get("topics") or []:
            if valid_topics and topic not in valid_topics:
                errors.append(f"{rel}: unknown topic `{topic}` (see data/topics.yaml)")

        # unrendered qmd sitting next to the page
        qmd = path.parent / "index.qmd"
        if qmd.exists() and qmd.stat().st_mtime > path.stat().st_mtime:
            warnings.append(
                f"{rel}: index.qmd is newer than index.md -- re-render with Quarto"
            )

        if H1_RE.search(body):
            warnings.append(
                f"{rel}: body contains an H1 (#) -- start at ## (title comes from frontmatter)"
            )
        for m in PLACEHOLDER_RE.finditer(body):
            warnings.append(f"{rel}: placeholder left in body: {m.group(0)!r}")
        if has_bare_code_fence(body):
            warnings.append(f"{rel}: fenced code block without a language tag")

        date = fm.get("date")
        if isinstance(date, datetime.date) and date > datetime.date.today():
            warnings.append(f"{rel}: date {date} is in the future")

    for w in warnings:
        console.print(f"[yellow]warning[/] {w}")
    for e in errors:
        console.print(f"[red]error[/]   {e}")

    failed = bool(errors) or (args.strict and bool(warnings))
    console.print(
        f"\n{len(targets)} note(s): [red]{len(errors)} error(s)[/], [yellow]{len(warnings)} warning(s)[/]"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
