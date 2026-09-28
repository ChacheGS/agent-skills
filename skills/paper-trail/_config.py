"""Where a repo keeps the things paper-trail checks.

The only thing this skill assumes about a layout is that this file
exists and says where everything is. Every other module takes a Config
and never guesses at a path.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = ".paper-trail.toml"

PATH_KEYS = ("decisions", "investigations", "index", "adr", "specs", "plans")

DEFAULT_INVESTIGATION_DAYS = 14


class PaperTrailError(Exception):
    """Something is wrong that a caller has to be told about.

    Raised both for a configuration that cannot be read and for a
    document that cannot be parsed. The entry point is what tells those
    apart: the first means nothing ran, the second means the record has a
    problem, and only one of those should stop a build.
    """


@dataclass(frozen=True)
class Config:
    root: Path
    mode: str
    skill_version: str
    decisions: Path
    investigations: Path
    index: Path
    adr: Path
    specs: Path
    plans: Path
    investigation_days: int


def load(root: Path) -> Config:
    """Read .paper-trail.toml, or say why it cannot be read."""
    root = Path(root).resolve()
    path = root / CONFIG_NAME
    if not path.is_file():
        raise PaperTrailError(
            f"{path} does not exist. paper-trail needs it to know where this repo "
            f"keeps its decisions; see the README for a starting one, or run "
            f"new.py --config to write it."
        )
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as broken:
        raise PaperTrailError(f"{path} is not valid TOML: {broken}") from None

    unknown = sorted(set(data) - {"mode", "skill_version", "paths", "thresholds"})
    if unknown:
        raise PaperTrailError(f"{path} has unknown top-level keys: {unknown}")
    thresholds = data.get("thresholds", {})
    extra = sorted(set(thresholds) - {"investigation_days"})
    if extra:
        # Same reason as [paths]: a typo leaves the real key at its
        # default and checks nothing, silently.
        raise PaperTrailError(f"{path} has unknown [thresholds] keys: {extra}")
    if data.get("mode", "vendored") not in ("vendored", "referenced"):
        raise PaperTrailError(
            f"{path}: mode is {data['mode']!r}; it is vendored or referenced"
        )

    paths = data.get("paths", {})
    missing = [key for key in PATH_KEYS if key not in paths]
    if missing:
        raise PaperTrailError(f"{path} names no {', '.join(missing)} under [paths]")
    unknown = sorted(set(paths) - set(PATH_KEYS))
    if unknown:
        # Loud rather than ignored: a typo'd key would otherwise leave the
        # real one at its default and check nothing, silently.
        raise PaperTrailError(f"{path} has unknown [paths] keys: {unknown}")

    return Config(
        root=root,
        mode=str(data.get("mode", "vendored")),
        skill_version=str(data.get("skill_version", "")),
        investigation_days=int(
            thresholds.get("investigation_days", DEFAULT_INVESTIGATION_DAYS)
        ),
        **{key: (root / paths[key]).resolve() for key in PATH_KEYS},
    )
