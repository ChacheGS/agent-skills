"""The skill's docs and files agree with its code.

These break where an adopter would find out the hard way: a module the
README forgot to list, a config key nobody documented.
"""

import re
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
import _config

README = (SKILL / "README.md").read_text(encoding="utf-8")


def vendored_in_readme() -> set[str]:
    """The names between "copy" and "into your repo" in the vendoring paragraph."""
    paragraph = re.search(r"copy (.*?) into your repo", README, re.DOTALL).group(1)
    return set(re.findall(r"`([^`]+)`", paragraph))


def shipped() -> set[str]:
    """What an adopter needs: the scripts, VERSION and templates, not tests or docs."""
    return {path.name for path in SKILL.glob("*.py")} | {"VERSION", "templates/"}


class Vendoring(unittest.TestCase):
    def test_the_readme_lists_exactly_the_files_that_ship(self):
        """A module missing from the list works here and raises ImportError
        in the first repo that vendors by the README."""
        listed = vendored_in_readme()

        self.assertIn("check.py", listed)  # the parse found something
        self.assertEqual(listed, shipped())


class ConfigKeys(unittest.TestCase):
    def test_every_path_key_is_in_the_starting_config(self):
        template = (SKILL / "templates" / "config.toml").read_text(encoding="utf-8")

        for key in _config.PATH_KEYS + _config.OPTIONAL_PATH_KEYS:
            self.assertRegex(template, rf"(?m)^#? ?{key} = ", key)

    def test_every_optional_key_is_in_the_readme(self):
        for key in _config.OPTIONAL_PATH_KEYS:
            self.assertIn(f"`{key}`", README, key)


if __name__ == "__main__":
    unittest.main()
