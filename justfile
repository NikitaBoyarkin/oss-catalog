set positional-arguments

# List all available recipes
default:
    @just --list

clean:
    rm -rf public

# Install Node.js dependencies (Pagefind; Tailwind if you add it)
install:
    yarn install

# Local development server with live reload
dev:
    hugo server -D --disableFastRender

# Build the static site (Hugo only -- no external tooling required)
build:
    hugo

# Build the Pagefind search index (run AFTER `just build`)
build-search:
    yarn build-search

# Fetch GitHub repository metadata -> data/github-repos.toml
update-github-repos *args:
    uv run scripts/update-github-repos.py {{args}}

# Merge github-repos.toml into project page frontmatter
update-project-frontmatter:
    uv run scripts/update-project-frontmatter.py

# Scaffold a new project page for a repo
create-new-project *args:
    uv run scripts/create-new-project.py {{args}}

# Validate note frontmatter and placement
validate-notes *args:
    uv run scripts/validate-notes.py {{args}}
