import os
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


def git(root, *args, when=None):
    """`when` sets the committer date, which is what "last touched" means
    and what the check reads. --date alone sets the author date, which a
    rebase preserves and git log does not show by default."""
    environment = dict(os.environ)
    if when is not None:
        environment["GIT_COMMITTER_DATE"] = when
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, env=environment
    )


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


class Investigations(unittest.TestCase):
    def test_without_git_the_check_skips_and_says_so(self):
        """A tarball has no history. A check that cannot run must not
        fail: exit 1 has to mean the record has a problem."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))
            (config.investigations / "0001-a-hunt.md").write_text("# a hunt\n")

            findings, skipped = _checks.stale_investigations(config)

            self.assertEqual(findings, [])
            self.assertIn("git", skipped)

    def test_an_investigation_nothing_has_touched_is_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))
            (config.investigations / "0001-a-hunt.md").write_text("# a hunt\n")
            git(config.root, "init", "-q")
            git(config.root, "add", "-A")
            git(
                config.root, "-c", "user.email=t@t", "-c", "user.name=t",
                "commit", "-q", "-m", "first",
                when="2020-01-01T00:00:00+00:00",
            )

            findings, skipped = _checks.stale_investigations(config)

            self.assertIsNone(skipped)
            self.assertEqual(len(findings), 1)
            self.assertIn("0001-a-hunt.md", findings[0].where)

    def test_an_investigation_touched_today_is_not_a_finding(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))
            (config.investigations / "0001-a-hunt.md").write_text("# a hunt\n")
            git(config.root, "init", "-q")
            git(config.root, "add", "-A")
            git(
                config.root, "-c", "user.email=t@t", "-c", "user.name=t",
                "commit", "-q", "-m", "first",
            )

            findings, skipped = _checks.stale_investigations(config)

            self.assertIsNone(skipped)
            self.assertEqual(findings, [])


class Stamp(unittest.TestCase):
    def test_a_vendored_copy_behind_the_skill_is_reported(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            config = fixtures.repo(root)
            (root / ".paper-trail.toml").write_text(
                'mode = "vendored"\nskill_version = "1.0.0"\n'
                + (root / ".paper-trail.toml").read_text()
            )
            import _config

            config = _config.load(root)

            findings = _checks.stamp_is_current(config, "1.1.0")

            self.assertEqual(len(findings), 1)
            self.assertIn("1.0.0", findings[0].what)

    def test_a_referenced_copy_cannot_drift(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))

            self.assertEqual(_checks.stamp_is_current(config, "9.9.9"), [])


class ExitCodes(unittest.TestCase):
    def test_a_missing_config_is_two_and_a_broken_decision_is_one(self):
        """The distinction is the contract: only one of these should stop
        a build, and a caller cannot tell them apart from the output."""
        import check

        with TemporaryDirectory() as name:
            self.assertEqual(check.main(["--root", name]), 2)

            config = fixtures.repo(Path(name), decisions=[("0001", "A thing", "body")])
            (config.decisions / "0002-unparseable.md").write_text("no frontmatter here\n")

            self.assertEqual(check.main(["--root", name]), 1)

    def test_a_clean_record_is_zero(self):
        import check

        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name), decisions=[("0001", "A thing", "body")])
            config.index.parent.mkdir(parents=True, exist_ok=True)
            config.index.write_text(
                _render.render(_docs.decisions(config), root=config.root, index=config.index)
            )

            self.assertEqual(check.main(["--root", name]), 0)


class PathsInProposals(unittest.TestCase):
    def test_a_plan_may_name_files_it_has_not_created_yet(self):
        """A plan is a dated proposal: naming a file it intends to write
        is its job. Asking it whether that file exists today turns the
        check into noise, which is how a check gets turned off."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name),
                extra={
                    "docs/plans/2026-01-01-a-plan.md": "Create `src/thing/new.py` for it.\n",
                    "docs/specs/a-design.md": "It will live at `src/thing/new.py`.\n",
                },
            )

            self.assertEqual(_checks.paths_exist(config), [])

    def test_a_decision_naming_a_file_that_moved_is_still_a_finding(self):
        """A decision describes what is, not what someone intends."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(
                Path(name), decisions=[("0001", "A thing", "it lives in `src/thing/gone.py`")]
            )

            self.assertEqual(len(_checks.paths_exist(config)), 1)


class AdrComments(unittest.TestCase):
    def test_a_trailing_comment_is_not_part_of_the_path(self):
        """Real ADRs carry them: `- docs/adr/adr_018.md  # why`. Reading
        the comment as part of the path reports a file nobody named."""
        with TemporaryDirectory() as name:
            path = Path(name) / "adr_017.md"
            path.write_text(
                "---\nrelated:\n  - docs/adr/adr_018.md  # and why it matters\n---\n"
            )

            self.assertEqual(_docs.adr_relations(path), ("docs/adr/adr_018.md",))
