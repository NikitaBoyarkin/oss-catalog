#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "rich>=13.0.0"]
# ///
"""Merge data/github-repos.toml into content/projects/*/index.md.

For each project page we read the `github: owner/name` field from its frontmatter, look up the
matching record in data/github-repos.toml, and (re)write:

  * `external:`  -- a machine-owned mirror of the record. DO NOT edit by hand.
  * top-level derived fields (currently `languages`), unless the page already sets them.

Per-page `exclude:` lets a human drop noisy data, e.g.:

  exclude:
    contributors: [some-bot]

Usage: uv run scripts/update-project-frontmatter.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import yaml
from rich.console import Console

console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "content" / "projects"
DATA_FILE = REPO_ROOT / "data" / "github-repos.toml"
AUTO_COMMENT = "# updated automatically, do not edit\n"


def split_frontmatter(text: str) -> tuple[dict, str] | None:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None
    try:
        fm = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    return fm, "\n".join(lines[end + 1 :])


def dump_fm(fm: dict) -> str:
    return (
        yaml.dump(
            fm, sort_keys=False, default_flow_style=False, allow_unicode=True
        ).rstrip()
        + "\n"
    )


def load_records() -> dict[str, dict]:
    with DATA_FILE.open("rb") as fh:
        data = tomllib.load(fh)
    return {r["repo"]: r for r in data.get("repos", [])}


def index_by_name(by_repo: dict[str, dict]) -> dict[str, dict]:
    return {r["name"]: r for r in by_repo.values()}


def find_record(
    github: str | None,
    dir_name: str,
    by_repo: dict[str, dict],
    by_name: dict[str, dict],
) -> dict | None:
    """Match a page to its TOML record: `owner/name`, then bare name, then the directory name."""
    return by_repo.get(github) or by_name.get(github) or by_name.get(dir_name)


def build_external(record: dict, exclude: dict | None = None) -> dict:
    """The machine-owned `external:` block, minus anything the page asks to drop."""
    external = {
        "description": record.get("description", ""),
        "stars": record.get("stars"),
        "forks": record.get("forks"),
        "releases": record.get("releases"),
        "latest_release": record.get("latest_release"),
        "first_commit": record.get("first_commit"),
        "last_updated": record.get("last_updated"),
        "license": record.get("license"),
        "languages": [record["language"]] if record.get("language") else [],
        "contributors": record.get("contributors", []),
    }

    # Honour per-page exclude lists.
    for key, drop in (exclude or {}).items():
        if key in external and isinstance(external[key], list):
            external[key] = [v for v in external[key] if v not in set(drop)]
    return external


def merge_frontmatter(fm: dict, external: dict) -> dict:
    """Editorial fields, with derived `languages` filled in only when the page omits them."""
    head = {k: v for k, v in fm.items() if k != "external"}
    if "languages" not in head and external["languages"]:
        head["languages"] = external["languages"]
    return head


def render_page(head: dict, external: dict, body: str) -> str:
    """Full file text for one project page."""
    return (
        f"---\n{dump_fm(head)}\n{AUTO_COMMENT}"
        f"{dump_fm({'external': external})}---\n{body}"
    )


def main() -> int:
    if not DATA_FILE.exists():
        console.print(
            f"[bold red]Error:[/] {DATA_FILE} not found. Run update-github-repos.py first."
        )
        return 1
    if not PROJECTS_DIR.exists():
        console.print(f"[yellow]No {PROJECTS_DIR} directory -- nothing to do.[/]")
        return 0

    by_repo = load_records()
    by_name = index_by_name(by_repo)
    updated = 0

    for page in sorted(PROJECTS_DIR.glob("*/index.md")):
        split = split_frontmatter(page.read_text(encoding="utf-8"))
        if split is None:
            console.print(
                f"[yellow]skip (no frontmatter):[/] {page.relative_to(REPO_ROOT)}"
            )
            continue
        fm, body = split

        record = find_record(fm.get("github"), page.parent.name, by_repo, by_name)
        if record is None:
            console.print(
                f"[yellow]skip (no GitHub record):[/] {page.relative_to(REPO_ROOT)}"
            )
            continue

        external = build_external(record, fm.get("exclude") or {})
        head = merge_frontmatter(fm, external)

        new_text = render_page(head, external, body)
        if new_text != page.read_text(encoding="utf-8"):
            page.write_text(new_text, encoding="utf-8")
            updated += 1
            console.print(f"[green]updated[/] {page.relative_to(REPO_ROOT)}")

    console.print(f"[bold green]Done.[/] {updated} page(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
