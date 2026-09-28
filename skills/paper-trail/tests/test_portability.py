import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]

# Anything naming a particular repo, or a build system this has no
# business knowing about.
FORBIDDEN = ("truck", "devvm", "make verify", "Makefile", "mise ", "uv run")


def _worth_reading(path: Path) -> bool:
    """Source and prose, not artifacts, and not this file.

    This one carries every forbidden word as a literal, so reading it
    would report itself for ever.
    """
    if {".git", "__pycache__"} & set(path.parts):
        return False
    return path != Path(__file__).resolve()


class Portability(unittest.TestCase):
    def test_no_file_names_a_repo_or_a_build_system(self):
        """This skill is installed into repos it has never seen. A path or
        a target name from the one it was extracted from would work until
        the day it moved, which is the worst time to find out."""
        offences = []
        read = []
        for path in sorted(SKILL.rglob("*")):
            if not path.is_file() or not _worth_reading(path):
                continue
            read.append(path.relative_to(SKILL))
            text = path.read_text(errors="ignore")
            offences += [
                f"{path.relative_to(SKILL)}: {word!r}" for word in FORBIDDEN if word in text
            ]

        # Without this the test passes by walking nothing, which is the
        # one way a guard like this fails silently.
        self.assertIn(Path("README.md"), read)
        self.assertIn(Path("_checks.py"), read)
        self.assertEqual(offences, [])
