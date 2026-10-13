#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "rich>=13.0.0"]
# ///
"""Set `topics` and `tags` on project pages from a curated mapping.

The catalog has a fixed topic set (data/topics.yaml) that powers the /topics/ hubs. This
script writes the mapping below into each page's frontmatter, preserving the machine-owned
`external:` block exactly. Edit the MAPPING here (or delete this script and edit pages by
hand) when a project's focus changes.

Usage:
  uv run scripts/set-project-taxonomy.py --dry-run
  uv run scripts/set-project-taxonomy.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from rich.console import Console

console = Console(stderr=True)
REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "content" / "projects"
TOPICS_FILE = REPO_ROOT / "data" / "topics.yaml"
AUTO_COMMENT = "# updated automatically, do not edit\n"

# repo folder name -> (topics, tags). Topics MUST come from data/topics.yaml.
MAPPING: dict[str, tuple[list[str], list[str]]] = {
    "ab_test": (["Experimentation"], ["experimentation", "methodology"]),
    "airflow": (["Data Engineering"], ["airflow", "etl", "data-quality"]),
    "browser-mini-games": ([], ["svg", "games", "astro"]),
    "case-ab": (["Experimentation", "Product Metrics"], ["cuped", "kyc", "hte"]),
    "case-anchor-cac": (["Product Metrics"], ["unit-economics", "ltv", "cac"]),
    "case-anomalies": (["Product Metrics"], ["anomaly-detection", "statistics"]),
    "case-assisted-cac": (["Product Metrics"], ["unit-economics", "cac", "ltv"]),
    "case-attribution": (["Product Metrics"], ["attribution", "marketing-mix"]),
    "case-causal-kyc": (
        ["Causal Inference", "Cohorts and Retention"],
        ["difference-in-differences", "retention"],
    ),
    "case-churn": (["Cohorts and Retention"], ["churn", "classification"]),
    "case-clv": (["Product Metrics", "Cohorts and Retention"], ["ltv", "gamma-gamma"]),
    "case-dormant-winback": (
        ["Experimentation", "Cohorts and Retention"],
        ["winback", "experimentation"],
    ),
    "case-funnel": (["Product Metrics"], ["funnel", "conversion"]),
    "case-fx-sourcing": (["Product Metrics"], ["unit-economics", "fx"]),
    "case-jtbd": (["Product Metrics"], ["jtbd", "segmentation"]),
    "case-kyc-45": (["Experimentation", "Causal Inference"], ["hte", "segmentation"]),
    "case-nps": (["Product Metrics"], ["nps", "survey"]),
    "case-premium-offers": (
        ["Experimentation", "Product Metrics"],
        ["segmentation", "offers"],
    ),
    "case-premium-upsell": (["Product Metrics"], ["conversion", "upsell"]),
    "case-referral": (["Product Metrics"], ["referral", "funnel"]),
    "case-retention": (["Cohorts and Retention"], ["cohorts", "retention", "ltv"]),
    "case-rfm": (["Cohorts and Retention", "Product Metrics"], ["rfm", "segmentation"]),
    "case-segmentation": (["Product Metrics"], ["kmeans", "segmentation"]),
    "case-spend": (["Product Metrics"], ["spend", "segmentation"]),
    "case-support-churn": (["Cohorts and Retention"], ["churn", "support"]),
    "case-unit-economics": (["Product Metrics"], ["unit-economics", "ltv", "cac"]),
    "causal-uplift": (["Causal Inference"], ["uplift", "causal-ml"]),
    "churn-prediction": (["Cohorts and Retention"], ["churn", "machine-learning"]),
    "crm-experiment-lab": (["Experimentation"], ["experimentation", "srm"]),
    "digital_garden": ([], ["knowledge-base", "obsidian"]),
    "ml": ([], ["machine-learning", "scikit-learn"]),
    "my_cv": ([], ["resume", "career"]),
    "NLTK": (["LLM and RAG"], ["nlp", "nltk"]),
    "NikitaBoyarkin": ([], ["profile"]),
    "NikitaBoyarkin.github.io": (["Dashboards and BI"], ["portfolio", "website"]),
    "python": ([], ["eda", "pandas", "python"]),
    "Python_algorithms": ([], ["algorithms", "python"]),
    "Python_data_structures": ([], ["data-structures", "python"]),
    "rag-eval-harness": (["LLM and RAG"], ["rag", "evaluation", "llm"]),
    "rfm-analysis-of-bank-clients": (
        ["Cohorts and Retention", "Product Metrics"],
        ["rfm", "segmentation"],
    ),
    "scrolly-english-speaking": ([], ["scrollytelling", "d3", "english"]),
    "serp-rank-lab": (
        ["Experimentation", "Product Metrics"],
        ["ranking", "serp", "position-bias"],
    ),
    "sql-analytics-case-study": (
        ["SQL Analytics", "Product Metrics"],
        ["sql", "case-study"],
    ),
    "tableau_cohort_analysis": (
        ["Cohorts and Retention", "Dashboards and BI"],
        ["tableau", "cohorts", "ltv"],
    ),
    "telegram_bot_public": ([], ["telegram", "bot"]),
    "TensorFlow-and-Keras": ([], ["deep-learning", "tensorflow"]),
    "volta-banking": (
        ["Product Metrics", "Data Engineering"],
        ["pipeline", "etl", "dbt"],
    ),
}


def split_frontmatter(text: str):
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


def dump_fm(obj) -> str:
    return (
        yaml.dump(
            obj, sort_keys=False, default_flow_style=False, allow_unicode=True
        ).rstrip()
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    valid_topics = (
        set(yaml.safe_load(TOPICS_FILE.read_text()) or [])
        if TOPICS_FILE.exists()
        else set()
    )

    for name, (topics, _tags) in MAPPING.items():
        unknown = [t for t in topics if valid_topics and t not in valid_topics]
        if unknown:
            console.print(f"[bold red]Error:[/] {name}: unknown topic(s) {unknown}")
            return 1

    changed = 0
    pages = sorted(PROJECTS_DIR.glob("*/_index.md"))
    for page in pages:
        name = page.parent.name
        split = split_frontmatter(page.read_text(encoding="utf-8"))
        if split is None:
            console.print(f"[yellow]skip (no frontmatter):[/] {name}")
            continue
        fm, body = split
        if name not in MAPPING:
            console.print(f"[dim]unmapped, left as-is:[/] {name}")
            continue

        topics, tags = MAPPING[name]
        fm["topics"] = list(topics)
        fm["tags"] = list(tags)

        head = {k: v for k, v in fm.items() if k != "external"}
        ext = fm.get("external")
        new_text = f"---\n{dump_fm(head)}\n"
        if ext is not None:
            new_text += f"{AUTO_COMMENT}{dump_fm({'external': ext})}"
        new_text += f"---\n{body}"

        if new_text != page.read_text(encoding="utf-8"):
            changed += 1
            if args.dry_run:
                console.print(
                    f"[cyan]would update[/] {name}: topics={topics} tags={tags}"
                )
            else:
                page.write_text(new_text, encoding="utf-8")
                console.print(f"[green]updated[/] {name}")

    console.print(
        f"[bold green]{'Would change' if args.dry_run else 'Changed'}[/] {changed} page(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
