# Analytics Project Catalog

A data-driven catalog of open-source projects: one page per repository, with metadata synced
from the GitHub API (stars, releases, contributors, language, license), cross-linked with notes
and learning resources.

Adapted from the `posit-dev/open-source-website` pattern (see the `oss-catalog-site` skill).
This is a **starter**: the data model, sync pipeline, validator, and CI are wired; the visual
layer is intentionally minimal and yours to grow.

## The one rule

`data/github-repos.toml` is the **source of truth** for machine-owned data. A sync script writes
it; a second script mirrors each record into a project page's `external:` frontmatter block.
Never hand-edit `external:` — correct noisy data through `exclude` on the page, or by fixing the
source repo.

## Layout

```
hugo.toml                     site config: taxonomies, permalinks, ignoreFiles, outputs
_quarto.yml                   Quarto -> Hugo-flavored Markdown
justfile                      task runner (the command surface)
data/github-repos.toml        GENERATED repo metadata (source of truth)
data/topics.yaml              fixed topic taxonomy
content/
  _index.md                   home
  projects/<name>/_index.md   one page per project
  notes/<slug>/               blog posts (index.md or index.qmd + rendered index.md)
  resources/_index.md         tutorials / notebooks / links
assets/css/main.css           hand-written CSS (Tailwind is an optional upgrade)
layouts/                      minimal templates (no external theme)
scripts/                      sync, scaffold, validate
.github/workflows/build.yml   build + warn-gate + search index
```

## Commands

```sh
uv run scripts/update-github-repos.py          # fetch repo metadata -> data/github-repos.toml
uv run scripts/update-project-frontmatter.py   # merge it into content/projects/*/_index.md
uv run scripts/create-new-project.py <name>    # scaffold a project page
uv run scripts/validate-notes.py               # validate note frontmatter + placement
uv run scripts/validate-notes.py --strict      # warnings become errors

just dev            # hugo server with live reload at http://localhost:1313
just build          # build the static site into public/
just build-search   # build the Pagefind index (after a build)
```

## Prerequisites

Hugo **extended** v0.128+, `uv` (Python), and optionally Node 20+ (Pagefind) and Quarto
(only for `index.qmd` notes). The base site builds with Hugo alone.

## Why not Tailwind out of the box

The reference implementation uses Tailwind + Pagefind. To keep `hugo` buildable with **zero**
external tooling, the starter ships hand-written CSS. Add Tailwind by putting
`@import "tailwindcss";` in `assets/css/main.css`, adding `@tailwindcss/cli` to `package.json`,
and switching `baseof.html` to Hugo's `css.TailwindCSS` pipe.

## Credits

Pattern derived from `posit-dev/open-source-website` (MIT).
