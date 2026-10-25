# Analytics Project Catalog

A data-driven catalog of open-source projects: one page per repository, with metadata synced
from the GitHub API (stars, releases, contributors, language, licence), cross-linked by topic,
tag and language.

Built with **Astro 7** (`output: 'static'`, zero client framework). The visual system is ported
from [NikitaBoyarkin.github.io](https://github.com/NikitaBoyarkin/NikitaBoyarkin.github.io):
the same tokens, self-hosted Inter + Cormorant, and the same card/button geometry — there is no
Tailwind and no third-party theme.

## The one rule

`data/github-repos.toml` is the **source of truth** for machine-owned data. A sync script writes
it; a second script mirrors each record into a project page's `external:` frontmatter block.
Never hand-edit `external:` — correct noisy data through `exclude` on the page, or by fixing the
source repo.

## Layout

```
astro.config.mjs               site config: site/base, integration list, sitemap
content/projects/<slug>/index.md   one page per project (frontmatter + Markdown body)
content/notes/<slug>/index.md      notes (dated, rendered at /notes/<slug>/)
data/github-repos.toml         GENERATED repo metadata (source of truth)
data/topics.yaml               fixed topic taxonomy
src/content.config.ts          collection schemas (projects, notes)
src/layouts/Base.astro         shell: head, sticky nav, theme toggle, footer
src/components/                ProjectCard, NoteCard
src/lib/                       site config + base-path helper, collection queries, formatting
src/pages/                     routes: /, /projects, /projects/<slug>, /notes, /notes/<slug>,
                               /topics|tags|languages (+ term pages), /resources,
                               /rss.xml, /llms.txt, /robots.txt
src/styles/global.css          design tokens + the whole visual system
scripts/                       sync, scaffold, validate (uv + PEP 723 inline deps)
.github/workflows/build.yml    validate -> type-check -> build -> Pagefind -> Pages
```

## Commands

```sh
bun install                    # dependencies
bun run dev                    # dev server at http://localhost:4321/oss-catalog/
bun run build                  # static build to dist/ + Pagefind index
bun run preview                # serve the built site
bun run check                  # astro check (types + content schemas)
bun run sync                   # regenerate astro:content types

bun run update-repos           # fetch repo metadata -> data/github-repos.toml
bun run update-frontmatter     # merge it into content/projects/*/index.md
bun run new-project <name>     # scaffold a project page
bun run set-taxonomy           # apply the curated topics/tags mapping
bun run validate               # validate note frontmatter + placement
```

## Prerequisites

Node 20+ or Bun 1.4+, and `uv` (Python) for the sync/validate scripts. The site itself needs no
Python: the build reads only the frontmatter that the scripts already wrote.

## Adding a page

```sh
bun run new-project my-repo     # creates content/projects/my-repo/index.md
bun run update-repos            # fills data/github-repos.toml
bun run update-frontmatter      # mirrors the record into `external:`
bun run build
```

A project page needs `title`, `description`, `github`, and (optionally) `topics`, `tags`,
`languages`. Missing `external` renders fine — the stats block simply omits the synced values.

## Deployment

Pushing to `main` triggers `.github/workflows/build.yml`: it validates notes, runs
`astro check` (the type gate that replaced the old Hugo warning grep), builds to `dist/`, indexes
it with Pagefind, and deploys to GitHub Pages at
**https://nikitaboarkin.github.io/oss-catalog/**. Pages must be set to *GitHub Actions* as the
source (Settings → Pages), done once via the API:

```sh
gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow
```

## Credits

Data-model pattern derived from `posit-dev/open-source-website` (MIT). Visual system ported from
the author's portfolio site.
