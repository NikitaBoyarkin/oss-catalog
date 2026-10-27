#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "rich>=13.0.0"]
# ///
"""Regression tests for the content scripts.

Covers the pure logic of `scripts/update-project-frontmatter.py` (record matching, the
machine-owned `external:` block, derived `languages`, render idempotency) and the project-page
half of `scripts/validate-notes.py`.

Run: uv run tests/test_scripts.py          (or: uv run python -m unittest discover tests)
No network, no writes inside the repo -- fixtures live in a TemporaryDirectory.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
REPO_ROOT = SCRIPTS.parent


def load_script(name: str, filename: str):
    """Import a hyphenated script file as a module (they are not a package)."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


upf = load_script("update_project_frontmatter", "update-project-frontmatter.py")
vn = load_script("validate_notes", "validate-notes.py")

RECORD = {
    "repo": "NikitaBoyarkin/ab_test",
    "name": "ab_test",
    "description": "A/B Testing Methodology Toolkit",
    "stars": 4,
    "forks": 0,
    "releases": 0,
    "latest_release": "",
    "first_commit": "2025-06-19T19:12:11+00:00",
    "last_updated": "2026-10-12T17:23:04+00:00",
    "license": "MIT",
    "language": "Python",
    "contributors": ["NikitaBoyarkin", "some-bot"],
}
BY_REPO = {RECORD["repo"]: RECORD}
BY_NAME = {RECORD["name"]: RECORD}
TOPICS = {"Experimentation", "Product Metrics"}


def write_page(root: Path, slug: str, frontmatter: str, body: str = "Body\n") -> Path:
    page = root / slug / "index.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
    return page


class SplitFrontmatterTest(unittest.TestCase):
    def test_parses_mapping_and_body(self):
        fm, body = upf.split_frontmatter("---\ntitle: x\n---\nhello\n")
        self.assertEqual(fm, {"title": "x"})
        self.assertEqual(body, "hello\n")

    def test_rejects_missing_fence(self):
        self.assertIsNone(upf.split_frontmatter("title: x\n---\n"))

    def test_rejects_unterminated_fence(self):
        self.assertIsNone(upf.split_frontmatter("---\ntitle: x\n"))

    def test_rejects_non_mapping(self):
        self.assertIsNone(upf.split_frontmatter("---\n- a\n- b\n---\nbody"))


class FindRecordTest(unittest.TestCase):
    def test_by_full_repo(self):
        self.assertIs(
            upf.find_record("NikitaBoyarkin/ab_test", "zzz", BY_REPO, BY_NAME), RECORD
        )

    def test_by_bare_name(self):
        self.assertIs(upf.find_record("ab_test", "zzz", BY_REPO, BY_NAME), RECORD)

    def test_by_directory_name(self):
        self.assertIs(upf.find_record(None, "ab_test", BY_REPO, BY_NAME), RECORD)

    def test_unknown_is_none(self):
        self.assertIsNone(
            upf.find_record("NikitaBoyarkin/nope", "nope", BY_REPO, BY_NAME)
        )


class BuildExternalTest(unittest.TestCase):
    def test_language_is_wrapped_in_list(self):
        self.assertEqual(upf.build_external(RECORD)["languages"], ["Python"])

    def test_missing_language_is_empty_list(self):
        self.assertEqual(upf.build_external({"repo": "a/b"})["languages"], [])

    def test_exclude_drops_matching_contributors(self):
        ext = upf.build_external(RECORD, {"contributors": ["some-bot"]})
        self.assertEqual(ext["contributors"], ["NikitaBoyarkin"])

    def test_exclude_ignores_unknown_keys(self):
        ext = upf.build_external(RECORD, {"nonsense": ["x"]})
        self.assertEqual(ext["contributors"], ["NikitaBoyarkin", "some-bot"])


class MergeFrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.external = upf.build_external(RECORD)

    def test_derives_languages_when_absent(self):
        head = upf.merge_frontmatter({"title": "ab_test"}, self.external)
        self.assertEqual(head["languages"], ["Python"])

    def test_preserves_explicit_languages(self):
        """A page that sets `languages` keeps its edit; the sync must not overwrite it."""
        head = upf.merge_frontmatter(
            {"title": "ab_test", "languages": ["R"]}, self.external
        )
        self.assertEqual(head["languages"], ["R"])

    def test_drops_stale_external_block(self):
        head = upf.merge_frontmatter({"title": "x", "external": {"stars": 999}}, self.external)
        self.assertNotIn("external", head)


class RenderPageTest(unittest.TestCase):
    def setUp(self):
        self.external = upf.build_external(RECORD)

    def test_render_is_idempotent(self):
        """Rendering a rendered page changes nothing -- the sync must reach a fixed point."""
        head = upf.merge_frontmatter({"title": "ab_test", "github": RECORD["repo"]}, self.external)
        first = upf.render_page(head, self.external, "Body\n")
        fm2, body2 = upf.split_frontmatter(first)
        self.assertEqual(body2, "Body\n")
        second = upf.render_page(upf.merge_frontmatter(fm2, self.external), self.external, body2)
        self.assertEqual(first, second)

    def test_render_marks_external_as_machine_owned(self):
        head = upf.merge_frontmatter({"title": "ab_test"}, self.external)
        text = upf.render_page(head, self.external, "Body\n")
        self.assertIn("updated automatically, do not edit", text)
        self.assertIn("stars: 4", text)


class ValidateProjectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, page, repos=None):
        return vn.validate_project(page, TOPICS, repos or {"NikitaBoyarkin/ab_test", "ab_test"})

    def test_good_page_passes(self):
        page = write_page(
            self.root,
            "ab_test",
            "title: ab_test\ngithub: NikitaBoyarkin/ab_test\ntopics:\n- Experimentation\nexternal:\n  stars: 4\n",
        )
        errors, warnings = self.check(page)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_github_is_an_error_naming_the_file(self):
        page = write_page(self.root, "ab_test", "title: ab_test\n")
        errors, _ = self.check(page)
        self.assertTrue(any("missing required field `github`" in e for e in errors))
        self.assertTrue(all(str(page) in e for e in errors))

    def test_malformed_frontmatter_is_an_error(self):
        page = self.root / "ab_test" / "index.md"
        page.parent.mkdir(parents=True)
        page.write_text("---\ntitle: ab_test\n", encoding="utf-8")
        errors, _ = self.check(page)
        self.assertTrue(any("missing or unparseable frontmatter" in e for e in errors))

    def test_bad_github_shape_is_an_error(self):
        page = write_page(self.root, "ab_test", "title: ab_test\ngithub: just-a-name\n")
        errors, _ = self.check(page)
        self.assertTrue(any("must look like owner/name" in e for e in errors))

    def test_unknown_repo_is_an_error(self):
        page = write_page(
            self.root, "ghost", "title: ghost\ngithub: NikitaBoyarkin/ghost\n"
        )
        errors, _ = self.check(page)
        self.assertTrue(any("no record in data/github-repos.toml" in e for e in errors))

    def test_unknown_topic_is_an_error(self):
        page = write_page(
            self.root,
            "ab_test",
            "title: ab_test\ngithub: NikitaBoyarkin/ab_test\ntopics:\n- Made Up\nexternal:\n  stars: 1\n",
        )
        errors, _ = self.check(page)
        self.assertTrue(any("unknown topic `Made Up`" in e for e in errors))

    def test_missing_external_is_a_warning(self):
        page = write_page(
            self.root, "ab_test", "title: ab_test\ngithub: NikitaBoyarkin/ab_test\n"
        )
        errors, warnings = self.check(page)
        self.assertEqual(errors, [])
        self.assertTrue(any("update-project-frontmatter.py" in w for w in warnings))


class RealTreeTest(unittest.TestCase):
    """The checks CI runs, run here too: they must stay green on the shipped content."""

    def test_validate_every_project_page(self):
        valid_topics = set(yaml.safe_load((REPO_ROOT / "data" / "topics.yaml").read_text()))
        known = vn.load_known_repos()
        self.assertIn("NikitaBoyarkin/ab_test", known)
        pages = sorted((REPO_ROOT / "content" / "projects").glob("*/index.md"))
        self.assertGreater(len(pages), 40)
        for page in pages:
            errors, _ = vn.validate_project(page, valid_topics, known)
            self.assertEqual(errors, [], f"{page} failed validation")

    def test_every_page_resolves_to_a_github_record(self):
        by_repo = upf.load_records()
        by_name = upf.index_by_name(by_repo)
        pages = sorted((REPO_ROOT / "content" / "projects").glob("*/index.md"))
        for page in pages:
            fm, _ = upf.split_frontmatter(page.read_text(encoding="utf-8"))
            self.assertIsNotNone(
                upf.find_record(fm.get("github"), page.parent.name, by_repo, by_name),
                f"{page} has no record in data/github-repos.toml",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
