#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "rich>=13.0.0"]
# ///
"""Scaffold a project page for a repository.

Creates content/projects/<name>/_index.md with a `github:` field. The machine-owned
`external:` block is added later by update-project-frontmatter.py -- do not hand-write it.

Usage:
  uv run scripts/create-new-project.py rfm-analysis-of-bank-clients
  uv run scripts/create-new-project.py other-owner/some-repo
  uv run scripts/create-new-project.py --all          # every repo in github-repos.toml
"""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

import yaml
from rich.console import Console

console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "github-repos.toml"
PROJECTS_DIR = REPO_ROOT / "content" / "projects"


def render_page(name: str, repo: str, description: str) -> str:
    """Frontmatter via yaml.dump so a description containing ': ' stays valid YAML."""
    fm = {
        "title": name,
        "description": description or "",
        "github": repo,
        "topics": [],
        "tags": [],
    }
    yaml_fm = yaml.dump(
        fm, sort_keys=False, default_flow_style=False, allow_unicode=True
    ).rstrip()
    return f"---\n{yaml_fm}\n---\n\n{description or ''}\n"


def load_records() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("rb") as fh:
        return tomllib.load(fh).get("repos", [])


def write_page(name: str, repo: str, description: str, force: bool) -> bool:
    dest = PROJECTS_DIR / name / "_index.md"
    if dest.exists() and not force:
        console.print(f"[yellow]exists, skipping:[/] {dest.relative_to(REPO_ROOT)}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_page(name, repo, description), encoding="utf-8")
    console.print(f"[green]created[/] {dest.relative_to(REPO_ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", help="repo name or owner/name")
    parser.add_argument(
        "--all", action="store_true", help="scaffold every repo in github-repos.toml"
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing page"
    )
    args = parser.parse_args()

    records = load_records()

    if args.all:
        if not records:
            console.print(
                "[bold red]Error:[/] no data/github-repos.toml. Run the sync first."
            )
            return 1
        created = sum(
            write_page(r["name"], r["repo"], r.get("description", ""), args.force)
            for r in records
        )
        console.print(f"[bold green]Done.[/] {created} page(s) created.")
        return 0

    if not args.target:
        parser.error("provide a repo name, owner/name, or --all")

    if "/" in args.target:
        repo, name = args.target, args.target.split("/", 1)[1]
    else:
        name = args.target
        match = next((r for r in records if r["name"] == name), None)
        repo = match["repo"] if match else f"unknown/{name}"

    description = next(
        (r.get("description", "") for r in records if r["repo"] == repo), ""
    )
    write_page(name, repo, description, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
