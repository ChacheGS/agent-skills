import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _config
import fixtures


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

    def test_an_unknown_thresholds_key_is_refused(self):
        """Same reason as [paths]: a typo leaves the real key at its
        default and checks nothing."""
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                "[paths]\n"
                + "".join(f'{key} = "docs/{key}"\n' for key in _config.PATH_KEYS)
                + "[thresholds]\ninvestigaton_days = 3\n",
                encoding="utf-8",
            )

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(root)

            self.assertIn("investigaton_days", str(refusal.exception))

    def test_an_unknown_top_level_key_is_refused(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                'skil_version = "1.0.0"\n[paths]\n'
                + "".join(f'{key} = "docs/{key}"\n' for key in _config.PATH_KEYS),
                encoding="utf-8",
            )

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(root)

            self.assertIn("skil_version", str(refusal.exception))

    def test_a_mode_that_is_neither_is_refused(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                "mode = 7\n[paths]\n"
                + "".join(f'{key} = "docs/{key}"\n' for key in _config.PATH_KEYS),
                encoding="utf-8",
            )

            with self.assertRaises(_config.PaperTrailError):
                _config.load(root)

    def test_an_investigations_index_that_is_not_a_path_is_refused(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                "[paths]\ninvestigations_index = 7\n"
                + "".join(f'{key} = "docs/{key}"\n' for key in _config.PATH_KEYS),
                encoding="utf-8",
            )

            with self.assertRaises(_config.PaperTrailError):
                _config.load(root)

    def test_scripts_with_a_referenced_mode_is_refused(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text(
                'mode = "referenced"\n[paths]\nscripts = "tools/paper-trail"\n'
                + "".join(f'{key} = "docs/{key}"\n' for key in _config.PATH_KEYS),
                encoding="utf-8",
            )

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(root)

            self.assertIn("referenced", str(refusal.exception))

    def test_debt_is_optional_and_absent_means_none(self):
        with TemporaryDirectory() as name:
            config = fixtures.repo(Path(name))

            self.assertIsNone(config.debt)
            self.assertIsNone(config.debt_index)

    def test_invalid_toml_says_so(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            (root / ".paper-trail.toml").write_text("[paths\n", encoding="utf-8")

            with self.assertRaises(_config.PaperTrailError) as refusal:
                _config.load(root)

            self.assertIn("valid TOML", str(refusal.exception))
