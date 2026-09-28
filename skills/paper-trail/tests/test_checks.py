import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _checks
import _docs
import _render
import fixtures


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class IndexIsCurrent(unittest.TestCase):
    def test_an_index_nobody_regenerated_is_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name), decisions=[("0001", "A thing", "body")])
            config.index.parent.mkdir(parents=True, exist_ok=True)
            config.index.write_text("# stale\n")

            findings = _checks.index_is_current(config)

            self.assertEqual(len(findings), 1)
            self.assertIn("index.py", findings[0].what)

    def test_a_regenerated_index_is_clean(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name), decisions=[("0001", "A thing", "body")])
            config.index.parent.mkdir(parents=True, exist_ok=True)
            config.index.write_text(
                _render.render(_docs.decisions(config), root=config.root, index=config.index)
            )

            self.assertEqual(_checks.index_is_current(config), [])


class LinksResolve(unittest.TestCase):
    def test_a_link_to_a_file_that_is_not_there_is_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[("0001", "A thing", "See [the spec](../specs/gone.md).")],
            )

            findings = _checks.links_resolve(config)

            self.assertEqual(len(findings), 1)
            self.assertIn("gone.md", findings[0].what)

    def test_a_link_whose_slug_changed_names_the_file_that_replaced_it(self):
        """The id is what survives a rename, and a finding carrying the
        correction is worth more than one that says "broken"."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[
                    ("0001", "New title", "x"),
                    ("0002", "Pointer", "See [it](./0001-old-title.md)."),
                ],
            )

            findings = _checks.links_resolve(config)

            self.assertEqual(len(findings), 1)
            self.assertIn("0001-new-title.md", findings[0].what)

    def test_a_link_inside_a_fence_is_not_reported(self):
        """Documentation quotes example links. Reporting those is how a
        link checker gets turned off."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[
                    ("0001", "A thing", "```\nSee [nothing](../specs/imaginary.md).\n```")
                ],
            )

            self.assertEqual(_checks.links_resolve(config), [])

    def test_a_link_in_a_code_span_is_not_reported(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[("0001", "A thing", "write `[x](../specs/imaginary.md)` here")],
            )

            self.assertEqual(_checks.links_resolve(config), [])

    def test_a_relative_link_resolves_against_the_file_that_carries_it(self):
        """docs/adr/adr_025.md saying ../specs/x.md means docs/specs/x.md,
        not the repo root's."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                extra={
                    "docs/adr/adr_025.md": "---\nrelated: []\n---\n\nSee [it](../specs/real.md).\n",
                    "docs/specs/real.md": "# real\n",
                },
            )

            self.assertEqual(_checks.links_resolve(config), [])

    def test_a_url_is_not_a_path(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[("0001", "A thing", "see [it](https://example.com/x.md)")],
            )

            self.assertEqual(_checks.links_resolve(config), [])


class RelationsExist(unittest.TestCase):
    def test_a_decision_citing_a_spec_that_is_not_there_is_a_finding(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            config = fixtures.repo(root, decisions=[("0001", "A thing", "body")])
            path = config.decisions / "0001-a-thing.md"
            path.write_text(path.read_text().replace("spec = []", 'spec = ["docs/specs/gone.md"]'))

            findings = _checks.relations_exist(config)

            self.assertEqual(len(findings), 1)
            self.assertIn("docs/specs/gone.md", findings[0].what)

    def test_an_adr_related_to_something_missing_is_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                extra={
                    "docs/adr/adr_001.md": "---\nrelated:\n  - docs/specs/gone.md\n---\n\n# one\n"
                },
            )

            findings = _checks.relations_exist(config)

            self.assertEqual(len(findings), 1)
            self.assertIn("adr_001.md", findings[0].where)


class PathsExist(unittest.TestCase):
    def test_a_backticked_path_that_moved_is_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[("0001", "A thing", "see `src/thing/addons.py` for it")],
            )

            findings = _checks.paths_exist(config)

            self.assertEqual(len(findings), 1)
            self.assertIn("src/thing/addons.py", findings[0].what)

    def test_a_bare_filename_is_not_a_claim_about_a_path(self):
        """`config.yaml` is a kind of file, not a particular one."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name), decisions=[("0001", "A thing", "every `config.yaml` has a slug")]
            )

            self.assertEqual(_checks.paths_exist(config), [])

    def test_a_path_that_is_there_is_not_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                decisions=[("0001", "A thing", "see `docs/specs/real.md`")],
                extra={"docs/specs/real.md": "# real\n"},
            )

            self.assertEqual(_checks.paths_exist(config), [])
