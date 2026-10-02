import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _docs
import _render


def decision(**overrides):
    fields = dict(
        id="0042",
        title="A node says what it is once",
        status="open",
        opened=date(2026, 9, 25),
        closed=None,
        conclusion="The accessory decides the transport.",
        adr=(),
        spec=(),
        plan=(),
        superseded_by=None,
        path=Path("/repo/docs/decisions/0042-a-node-says-what-it-is-once.md"),
        body="",
    )
    fields.update(overrides)
    return _docs.Decision(**fields)


WHERE = dict(root=Path("/repo"), index=Path("/repo/docs/index.md"))


class Rendering(unittest.TestCase):
    def test_open_decisions_come_before_closed_ones(self):
        """The file answers "what is still open" at a glance, which is the
        one property a table had and this must not lose."""
        text = _render.render(
            [
                decision(id="0001", title="Closed", status="resolved", closed=date(2026, 9, 1)),
                decision(id="0002", title="Open"),
            ],
            **WHERE,
        )

        self.assertLess(text.index("[Open]"), text.index("[Closed]"))

    def test_a_title_with_a_pipe_is_escaped(self):
        """An unescaped pipe renders the row with an extra column, which
        is a defect that can sit unnoticed for months."""
        text = _render.render([decision(title="STARTED|BUSY, and what that cost")], **WHERE)

        self.assertIn(r"STARTED\|BUSY", text)

    def test_the_index_is_a_pure_projection(self):
        """Same decisions, same bytes, whatever order they were found in.
        A renderer that depended on that would make the is-it-current
        check fail at random."""
        items = [decision(id="0001", title="One"), decision(id="0002", title="Two")]

        self.assertEqual(
            _render.render(items, **WHERE), _render.render(list(reversed(items)), **WHERE)
        )

    def test_the_link_is_relative_to_the_index(self):
        """The index is not at the repo root, so a root-relative link
        would be wrong from the file that carries it."""
        text = _render.render(
            [decision()],
            root=Path("/repo"),
            index=Path("/repo/docs/prd/section_07_open_decisions.md"),
        )

        self.assertIn("(../decisions/0042-a-node-says-what-it-is-once.md)", text)

    def test_an_empty_record_still_renders(self):
        text = _render.render([], **WHERE)

        self.assertIn("Nothing open", text)


def investigation(**overrides):
    fields = dict(
        id="0003",
        title="Why the bus stalls",
        opened=date(2026, 9, 25),
        answered=None,
        decision=None,
        path=Path("/repo/docs/investigations/0003-why-the-bus-stalls.md"),
        body="## Symptom\n\nIt stalls.\n\n## Next\n\nProbe the clock line.\n\nThen the data line.\n",
    )
    fields.update(overrides)
    return _docs.Investigation(**fields)


LISTING = Path("/repo/docs/INVESTIGATIONS.md")


class RenderingInvestigations(unittest.TestCase):
    def test_an_open_one_shows_where_the_hunt_stands(self):
        text = _render.render_investigations([investigation()], [], index=LISTING)

        self.assertIn("| Probe the clock line. |", text)
        self.assertNotIn("Then the data line", text)

    def test_an_answered_one_links_the_decision_that_kept_its_conclusion(self):
        text = _render.render_investigations(
            [investigation(answered=date(2026, 10, 1), decision="0042")],
            [decision()],
            index=LISTING,
        )

        self.assertIn("(decisions/0042-a-node-says-what-it-is-once.md)", text)
        self.assertLess(text.index("## Open"), text.index("## Answered"))

    def test_a_file_with_no_next_section_still_renders(self):
        text = _render.render_investigations([investigation(body="just notes")], [], index=LISTING)

        self.assertIn("[Why the bus stalls]", text)

    def test_an_empty_record_still_renders(self):
        text = _render.render_investigations([], [], index=LISTING)

        self.assertIn("Nothing open", text)
        self.assertIn("Nothing answered yet", text)
