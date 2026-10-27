#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "rich>=13.0.0"]
# ///
"""Validate note AND project-page frontmatter.

Checks the mechanical things a reviewer should not have to: required metadata, valid taxonomy
values, correct placement, and unrendered .qmd sources. Project pages additionally have to name a
`github:` repo that exists in `data/github-repos.toml`, otherwise
`update-project-frontmatter.py` can skip them silently. A missing `external:` block is a warning
(therefore an error under `--strict`, which is what CI runs). Content review
(description drift, placeholders, alt text) is left to a human or the `review-post` style pass.

`astro check` also type-checks both collections against `src/content.config.ts`, but it runs after
`bun install` and knows nothing about data/topics.yaml or data/github-repos.toml -- this script is
the cheap gate that runs first.

Usage:
  uv run scripts/validate-notes.py                       # all notes + project pages
  uv run scripts/validate-notes.py content/notes/x/index.md
  uv run scripts/validate-notes.py content/projects/ab_test/index.md
  uv run scripts/validate-notes.py --projects-only       # skip notes
  uv run scripts/validate-notes.py --strict              # warnings become errors
"""

from __future__ import annotations

import argparse
import datetime
import re
import tomllib
from pathlib import Path

import yaml
from rich.console import Console

console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "content" / "notes"
PROJECTS_DIR = REPO_ROOT / "content" / "projects"
TOPICS_FILE = REPO_ROOT / "data" / "topics.yaml"
REPOS_FILE = REPO_ROOT / "data" / "github-repos.toml"

REQUIRED_FIELDS = ["title", "date", "description", "topics"]
PROJECT_REQUIRED_FIELDS = ["title", "github"]
GITHUB_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
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


def load_known_repos() -> set[str]:
    """Keys a project page's `github:` field may resolve to.

    Mirrors `update-project-frontmatter.py`: a page matches a record by `owner/name`, by bare
    repo name, or by its directory name. Returns an empty set when the TOML is absent.
    """
    if not REPOS_FILE.exists():
        return set()
    with REPOS_FILE.open("rb") as fh:
        try:
            data = tomllib.load(fh)
        except tomllib.TOMLDecodeError:
            return set()
    keys: set[str] = set()
    for r in data.get("repos", []):
        for key in ("repo", "name"):
            if r.get(key):
                keys.add(r[key])
    return keys


def display_path(path: Path) -> Path | str:
    """Repo-relative when inside the repo, absolute otherwise (fixtures live outside it)."""
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path


def validate_note(path: Path, valid_topics: set[str]) -> tuple[list[str], list[str]]:
    """Errors and warnings for one note page."""
    errors: list[str] = []
    warnings: list[str] = []
    rel = display_path(path)
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    if fm is None or not isinstance(fm, dict):
        return [f"{rel}: missing or unparseable frontmatter"], warnings

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
    return errors, warnings


def validate_project(
    path: Path, valid_topics: set[str], known_repos: set[str]
) -> tuple[list[str], list[str]]:
    """Errors and warnings for one project page.

    A broken page here is worse than a broken note: the project grid, the per-page metadata and
    the llms.txt feed all read from these files, and `update-project-frontmatter.py` skips a page
    whose `github:` resolves to nothing without failing.
    """
    errors: list[str] = []
    warnings: list[str] = []
    rel = display_path(path)
    fm, _body = split_frontmatter(path.read_text(encoding="utf-8"))
    if fm is None or not isinstance(fm, dict):
        return [f"{rel}: missing or unparseable frontmatter"], warnings

    for field in PROJECT_REQUIRED_FIELDS:
        if not fm.get(field):
            errors.append(f"{rel}: missing required field `{field}`")

    github = fm.get("github")
    if github:
        if not isinstance(github, str) or not GITHUB_RE.match(github):
            errors.append(f"{rel}: `github` must look like owner/name, got {github!r}")
        elif known_repos and not (
            {github, path.parent.name} & known_repos
        ):
            errors.append(
                f"{rel}: github repo `{github}` has no record in data/github-repos.toml"
            )

    for topic in fm.get("topics") or []:
        if valid_topics and topic not in valid_topics:
            errors.append(f"{rel}: unknown topic `{topic}` (see data/topics.yaml)")

    if "external" not in fm:
        warnings.append(
            f"{rel}: no `external` block -- run scripts/update-project-frontmatter.py"
        )
    return errors, warnings


def is_project_page(path: Path) -> bool:
    try:
        path.resolve().relative_to(PROJECTS_DIR.resolve())
    except ValueError:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    parser.add_argument(
        "--projects-only",
        action="store_true",
        help="skip notes, validate content/projects only",
    )
    args = parser.parse_args()

    valid_topics = (
        set(yaml.safe_load(TOPICS_FILE.read_text()) or [])
        if TOPICS_FILE.exists()
        else set()
    )
    known_repos = load_known_repos()

    if args.paths:
        note_targets = []
        project_targets = []
        for p in (Path(p) for p in args.paths):
            (project_targets if is_project_page(p) else note_targets).append(p)
    else:
        note_targets = (
            []
            if args.projects_only
            else (sorted(NOTES_DIR.glob("**/index.md")) if NOTES_DIR.exists() else [])
        )
        project_targets = (
            sorted(PROJECTS_DIR.glob("*/index.md")) if PROJECTS_DIR.exists() else []
        )

    errors: list[str] = []
    warnings: list[str] = []

    for path in note_targets:
        e, w = validate_note(path, valid_topics)
        errors.extend(e)
        warnings.extend(w)
    for path in project_targets:
        e, w = validate_project(path, valid_topics, known_repos)
        errors.extend(e)
        warnings.extend(w)

    for w in warnings:
        console.print(f"[yellow]warning[/] {w}")
    for e in errors:
        console.print(f"[red]error[/]   {e}")

    failed = bool(errors) or (args.strict and bool(warnings))
    console.print(
        f"\n{len(note_targets)} note(s), {len(project_targets)} project page(s): "
        f"[red]{len(errors)} error(s)[/], [yellow]{len(warnings)} warning(s)[/]"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
