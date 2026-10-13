#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyGithub>=2.1.1",
#   "tomli-w>=1.0.0",
#   "rich>=13.0.0",
# ]
# ///
"""Fetch public repository metadata from GitHub and write data/github-repos.toml.

This file is the SOURCE OF TRUTH for machine-owned project data. Never hand-edit it;
re-run this script instead. `update-project-frontmatter.py` mirrors each record into the
matching content/projects/<name>/index.md under an `external:` block.

Usage:
  uv run scripts/update-github-repos.py                     # default owner, cached
  uv run scripts/update-github-repos.py --owner someone     # another owner/org
  uv run scripts/update-github-repos.py --refresh           # ignore the cache, refetch
  uv run scripts/update-github-repos.py --with-contributors # slower, adds contributor logins
  uv run scripts/update-github-repos.py --skip-images       # skip per-repo README image lookup
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import tomli_w
from github import Auth, Github, GithubException, UnknownObjectException
from rich.console import Console

console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OWNER = "NikitaBoyarkin"
MAX_CONTRIBUTORS = 60
CACHE_MAX_AGE_H = 24

HTML_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")


def get_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        )
        if out.stdout.strip():
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    console.print(
        "[bold red]Error:[/] no GitHub token. Set GH_TOKEN/GITHUB_TOKEN or run `gh auth login`."
    )
    sys.exit(1)


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def readme_image(repo) -> str:
    """First non-badge image URL from the README, best effort."""
    try:
        content = repo.get_readme().decoded_content.decode("utf-8", "replace")
    except (GithubException, UnknownObjectException):
        return ""
    for match in list(HTML_IMG_RE.finditer(content)) + list(
        MD_IMG_RE.finditer(content)
    ):
        src = match.group(1)
        if "badge" not in src.lower():
            return src
    return ""


def release_info(repo) -> tuple[str, int]:
    latest, count = "", 0
    try:
        count = repo.get_releases().totalCount
    except GithubException:
        pass
    try:
        latest = iso(repo.get_latest_release().published_at)
    except (GithubException, UnknownObjectException):
        pass
    return latest, count


def contributors(repo) -> list[str]:
    """Contributor logins, minus GitHub App/bot accounts (`name[bot]`)."""
    try:
        logins = [c.login for c in repo.get_contributors()[:MAX_CONTRIBUTORS]]
    except GithubException:
        return []
    return [login for login in logins if "[bot]" not in login.lower()]


def build_record(repo, *, with_contributors: bool, skip_images: bool) -> dict:
    latest, count = release_info(repo)
    license_id = ""
    if repo.license is not None:
        license_id = repo.license.spdx_id or repo.license.name or ""
    return {
        "repo": repo.full_name,
        "name": repo.name,
        "description": repo.description or "",
        "website": repo.homepage or "",
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "latest_release": latest,
        "releases": count,
        "first_commit": iso(repo.created_at),
        "last_updated": iso(repo.updated_at),
        "license": license_id,
        "language": repo.language or "",
        "topics": sorted(repo.topics or []),
        "contributors": contributors(repo) if with_contributors else [],
        "readme_image": "" if skip_images else readme_image(repo),
    }


def fetch_records(
    owner: str, limit: int, with_contributors: bool, skip_images: bool
) -> list[dict]:
    gh = Github(auth=Auth.Token(get_token()))
    repos = list(gh.get_user(owner).get_repos(type="public", sort="updated"))
    repos = [r for r in repos if not r.fork and not r.archived]
    if limit:
        repos = repos[:limit]
    console.print(
        f"Fetching metadata for [bold]{len(repos)}[/] public repos of {owner} ..."
    )
    records = []
    for i, repo in enumerate(repos, 1):
        console.print(f"  [{i:>3}/{len(repos)}] {repo.full_name}")
        records.append(
            build_record(
                repo, with_contributors=with_contributors, skip_images=skip_images
            )
        )
    records.sort(key=lambda r: (-r["stars"], r["name"].lower()))
    return records


def load_cache(cache_file: Path) -> list[dict] | None:
    if not cache_file.exists():
        return None
    age_h = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600
    if age_h > CACHE_MAX_AGE_H:
        return None
    try:
        return json.loads(cache_file.read_text())
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument(
        "--output", default=str(REPO_ROOT / "data" / "github-repos.toml")
    )
    parser.add_argument(
        "--cache-file", default=str(REPO_ROOT / "data" / ".cache" / "repos.json")
    )
    parser.add_argument(
        "--refresh", action="store_true", help="ignore the cache and refetch"
    )
    parser.add_argument("--with-contributors", action="store_true")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=0, help="cap number of repos (0 = all)"
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=["NikitaBoyarkin/oss-catalog"],
        metavar="OWNER/NAME",
        help="repo to omit (repeatable; defaults to this catalog itself)",
    )
    args = parser.parse_args()

    cache_file = Path(args.cache_file)
    records = None if args.refresh else load_cache(cache_file)
    if records is not None:
        console.print(
            f"[cyan]Using cached records[/] ({cache_file}, {len(records)} repos)"
        )
    else:
        records = fetch_records(
            args.owner, args.limit, args.with_contributors, args.skip_images
        )
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(records, ensure_ascii=False, indent=2))

    excludes = set(args.exclude or [])
    if excludes:
        records = [r for r in records if r["repo"] not in excludes]

    # Normalise at write time so a stale cache can't leak bot accounts back in.
    for r in records:
        r["contributors"] = [
            c for c in r.get("contributors", []) if "[bot]" not in c.lower()
        ]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fh:
        tomli_w.dump({"repos": records}, fh)
    console.print(f"[bold green]Wrote[/] {out} ({len(records)} repos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
