"""The skill keeps its own record, and its own checks pass on it."""

import contextlib
import io
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
import _config
import _docs
import check


class Dogfood(unittest.TestCase):
    def test_the_skills_own_record_checks_out(self):
        """A stale index, a dead path or a comment citing a decision that
        moved fails here, in the one repo that has to follow its own rules."""
        # Without this the run passes by reading an empty record.
        self.assertGreaterEqual(len(_docs.decisions(_config.load(SKILL))), 1)

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = check.main(["--root", str(SKILL)])

        self.assertEqual(code, 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()
