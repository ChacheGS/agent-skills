import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _config


class Loading(unittest.TestCase):
    def test_paths_come_back_absolute_under_the_root(self):
        """Every caller joins these against files it found by walking, so
        a relative path here would resolve against the working directory
        rather than the repo."""
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                'mode = "referenced"\n'
                'skill_version = "1.0.0"\n'
                "[paths]\n"
                'decisions = "docs/decisions"\n'
                'investigations = "docs/investigations"\n'
                'index = "docs/index.md"\n'
                'adr = "docs/adr"\n'
                'specs = "docs/specs"\n'
                'plans = "docs/plans"\n'
            )

            config = _config.load(root)

            self.assertEqual(config.decisions, root.resolve() / "docs" / "decisions")
            self.assertTrue(config.index.is_absolute())

    def test_a_missing_config_says_what_writes_one(self):
        with TemporaryDirectory() as name:
            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(Path(name))

            self.assertIn("README", str(refusal.exception))

    def test_an_unknown_paths_key_is_refused(self):
        """A typo would leave the real key at its default and check
        nothing, which is worse than not running."""
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                "[paths]\n"
                + "".join(f'{key} = "docs/{key}"\n' for key in _config.PATH_KEYS)
                + 'decisons = "docs/typo"\n'
            )

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(root)

            self.assertIn("decisons", str(refusal.exception))

    def test_a_missing_paths_key_names_it(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text('[paths]\ndecisions = "docs/decisions"\n')

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(root)

            self.assertIn("investigations", str(refusal.exception))
