import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _config
import _docs

DECISION = """+++
id = "0042"
title = "A node says what it is once"
status = "open"
opened = 2026-09-25
conclusion = "The accessory decides the transport."
adr = []
spec = []
plan = []
+++

The body, which a table cell could not hold.
"""


class Frontmatter(unittest.TestCase):
    def test_the_fences_are_split_from_the_body(self):
        fields, body = _docs.frontmatter(DECISION)

        self.assertEqual(fields["id"], "0042")
        self.assertEqual(fields["opened"], date(2026, 9, 25))
        self.assertEqual(body.strip(), "The body, which a table cell could not hold.")

    def test_a_file_with_no_fences_is_refused(self):
        """Every decision is read for the index, so one that silently
        contributed nothing would vanish from it."""
        with self.assertRaises(_config.PaperTrailError) as refusal:
            _docs.frontmatter("# Just a heading\n")

        self.assertIn("+++", str(refusal.exception))

    def test_frontmatter_that_is_never_closed_is_refused(self):
        with self.assertRaises(_config.PaperTrailError) as refusal:
            _docs.frontmatter('+++\nid = "0001"\n')

        self.assertIn("never closed", str(refusal.exception))


class Discovery(unittest.TestCase):
    def repo(self, name, **files):
        root = Path(name)
        (root / "docs" / "decisions").mkdir(parents=True)
        for filename, text in files.items():
            (root / "docs" / "decisions" / filename).write_text(text)
        (root / ".paper-trail.toml").write_text(
            "[paths]\n"
            'decisions = "docs/decisions"\n'
            'investigations = "docs/investigations"\n'
            'index = "docs/index.md"\n'
            'adr = "docs/adr"\n'
            'specs = "docs/specs"\n'
            'plans = "docs/plans"\n'
        )
        return _config.load(root)

    def test_decisions_come_back_ordered_by_id(self):
        with TemporaryDirectory() as name:
            config = self.repo(
                name,
                **{
                    "0007-later.md": DECISION.replace('"0042"', '"0007"'),
                    "0042-earlier.md": DECISION,
                },
            )

            self.assertEqual([item.id for item in _docs.decisions(config)], ["0007", "0042"])

    def test_two_files_sharing_an_id_are_refused_naming_both(self):
        """Links resolve by id prefix, so a duplicate is a link that
        silently points at whichever file sorted first."""
        with TemporaryDirectory() as name:
            config = self.repo(name, **{"0042-one.md": DECISION, "0042-two.md": DECISION})

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _docs.decisions(config)

            self.assertIn("0042-one.md", str(refusal.exception))
            self.assertIn("0042-two.md", str(refusal.exception))

    def test_a_filename_that_disagrees_with_its_id_is_refused(self):
        with TemporaryDirectory() as name:
            config = self.repo(name, **{"0099-mismatch.md": DECISION})

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _docs.decisions(config)

            self.assertIn("0042", str(refusal.exception))

    def test_a_file_not_named_for_an_id_is_refused(self):
        with TemporaryDirectory() as name:
            config = self.repo(name, **{"notes.md": DECISION})

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _docs.decisions(config)

            self.assertIn("NNNN-slug.md", str(refusal.exception))

    def test_a_status_outside_the_set_is_refused(self):
        with TemporaryDirectory() as name:
            config = self.repo(
                name, **{"0042-a.md": DECISION.replace('"open"', '"in progress"')}
            )

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _docs.decisions(config)

            self.assertIn("in progress", str(refusal.exception))

    def test_a_superseded_decision_names_what_replaced_it(self):
        """A dead end with no forwarding address is the shape this design
        exists to remove."""
        with TemporaryDirectory() as name:
            config = self.repo(
                name,
                **{
                    "0042-a.md": DECISION.replace('"open"', '"superseded"').replace(
                        "adr = []", "closed = 2026-09-26\nadr = []"
                    )
                },
            )

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _docs.decisions(config)

            self.assertIn("the trail stops here", str(refusal.exception))

    def test_a_missing_decisions_directory_is_empty_rather_than_an_error(self):
        """A repo that has adopted the skill and not written a decision
        yet is a normal state, not a broken one."""
        with TemporaryDirectory() as name:
            config = self.repo(name)
            for path in config.decisions.iterdir():
                path.unlink()
            config.decisions.rmdir()

            self.assertEqual(_docs.decisions(config), [])


class AdrRelations(unittest.TestCase):
    def test_a_related_list_is_read(self):
        with TemporaryDirectory() as name:
            path = Path(name) / "adr_025.md"
            path.write_text(
                "---\n"
                "date: 2026-09-26\n"
                "status: accepted\n"
                "related:\n"
                "  - docs/adr/adr_024.md\n"
                "  - docs/specs/a-design.md\n"
                "---\n\n# ADR-025\n"
            )

            self.assertEqual(
                _docs.adr_relations(path),
                ("docs/adr/adr_024.md", "docs/specs/a-design.md"),
            )

    def test_an_empty_related_list_reads_as_nothing(self):
        with TemporaryDirectory() as name:
            path = Path(name) / "adr_001.md"
            path.write_text("---\ndate: 2026-01-01\nrelated: []\n---\n")

            self.assertEqual(_docs.adr_relations(path), ())

    def test_a_file_with_no_frontmatter_reads_as_nothing(self):
        with TemporaryDirectory() as name:
            path = Path(name) / "notes.md"
            path.write_text("# just prose\n")

            self.assertEqual(_docs.adr_relations(path), ())

    def test_a_shape_the_reader_does_not_know_is_refused(self):
        """A parser that silently misreads is worse than one that stops:
        returning () here would report every ADR as citing nothing."""
        with TemporaryDirectory() as name:
            path = Path(name) / "adr_099.md"
            path.write_text("---\nrelated: {a: 1}\n---\n")

            with self.assertRaises(_config.PaperTrailError):
                _docs.adr_relations(path)


class ClosedWithoutADate(unittest.TestCase):
    def test_a_resolved_decision_with_no_date_still_parses(self):
        """Migrated history often does not know when something closed, and
        a guess would be worse than a gap. The file is well formed; the
        gap is a finding rather than a refusal."""
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / "docs" / "decisions").mkdir(parents=True)
            (root / "docs" / "decisions" / "0001-a-thing.md").write_text(
                DECISION.replace('"0042"', '"0001"').replace('"open"', '"resolved"')
            )
            (root / ".paper-trail.toml").write_text(
                "[paths]\n"
                'decisions = "docs/decisions"\ninvestigations = "docs/i"\nindex = "docs/x.md"\n'
                'adr = "docs/adr"\nspecs = "docs/s"\nplans = "docs/p"\n'
            )

            item = _docs.decisions(_config.load(root))[0]

            self.assertEqual(item.status, "resolved")
            self.assertIsNone(item.closed)
