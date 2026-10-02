import contextlib
import io
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fixtures
import new
import status


def run(root):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = status.main(["--root", str(root)])
    return code, out.getvalue()


class Status(unittest.TestCase):
    def test_it_lists_what_is_open_in_each_kind(self):
        with TemporaryDirectory() as name:
            fixtures.repo(Path(name), debt="docs/debt")
            for kind, title in (("decision", "Pick a store"), ("investigation", "Bus stalls"), ("debt", "Global lock")):
                with contextlib.redirect_stdout(io.StringIO()):
                    new.main(["--root", name, kind, title])

            code, text = run(name)

            self.assertEqual(code, 0)
            self.assertIn("decisions: 1 open, 0 settled", text)
            self.assertIn("0001 Pick a store", text)
            self.assertIn("investigations: 1 open", text)
            self.assertIn("debt: 1 open", text)
            self.assertIn("0001 Global lock", text)

    def test_debt_is_left_out_when_the_repo_keeps_none(self):
        with TemporaryDirectory() as name:
            fixtures.repo(Path(name))

            self.assertNotIn("debt:", run(name)[1])

    def test_a_file_that_does_not_parse_is_counted_not_hidden(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))
            (config.decisions / "0001-broken.md").write_text("no frontmatter")

            self.assertIn("1 file(s) do not parse", run(name)[1])

    def test_no_config_is_exit_two(self):
        with TemporaryDirectory() as name:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(status.main(["--root", name]), 2)


if __name__ == "__main__":
    unittest.main()
