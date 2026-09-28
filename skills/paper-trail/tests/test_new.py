import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _config
import _docs
import fixtures
import new


class Naming(unittest.TestCase):
    def test_the_next_id_follows_the_highest(self):
        self.assertEqual(new.next_id(["0001", "0009"]), "0010")

    def test_the_first_id_is_one(self):
        self.assertEqual(new.next_id([]), "0001")

    def test_a_slug_is_lowercase_and_hyphenated(self):
        self.assertEqual(new.slug("A node says what it is once"), "a-node-says-what-it-is-once")

    def test_a_slug_drops_what_a_filename_cannot_carry(self):
        self.assertEqual(new.slug("STARTED|BUSY: what now?"), "started-busy-what-now")


class Writing(unittest.TestCase):
    def test_a_new_decision_parses_as_one(self):
        """A scaffold that does not parse is worse than none: the next
        check run fails on a file nobody has written yet."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))

            new.main(["--root", str(config.root), "decision", "A node says what it is once"])

            items = _docs.decisions(config)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].title, "A node says what it is once")
            self.assertEqual(items[0].status, "open")

    def test_a_second_decision_takes_the_next_id(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))

            new.main(["--root", str(config.root), "decision", "One"])
            new.main(["--root", str(config.root), "decision", "Two"])

            self.assertEqual([item.id for item in _docs.decisions(config)], ["0001", "0002"])

    def test_a_new_investigation_carries_the_four_headings(self):
        """Symptom, established, refuted, next. The third and fourth are
        what make picking a thread back up cheap."""
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))

            new.main(["--root", str(config.root), "investigation", "Coverage writes nothing"])

            written = (config.investigations / "0001-coverage-writes-nothing.md").read_text()
            for heading in ("## Symptom", "## Established", "## Refuted", "## Next"):
                self.assertIn(heading, written)

    def test_the_config_can_be_written_before_anything_else_exists(self):
        """_config's refusal promises this, and a new adopter has nothing
        to read a config from."""
        with TemporaryDirectory() as name:
            root = Path(name)

            new.main(["--root", str(root), "--config"])

            config = _config.load(root)
            self.assertEqual(config.mode, "vendored")
