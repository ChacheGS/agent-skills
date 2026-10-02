"""A repo on disk, for the checks to read."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _config

DECISION = """+++
id = "{id}"
title = "{title}"
status = "open"
opened = 2026-09-25
conclusion = "A conclusion."
adr = []
spec = []
plan = []
+++

{body}
"""


def repo(root: Path, *, decisions=(), extra=None, cites=None, investigations_index=None) -> _config.Config:
    """A configured repo with the directories the checks walk."""
    for name in ("decisions", "investigations", "adr", "specs", "plans"):
        (root / "docs" / name).mkdir(parents=True, exist_ok=True)
    for id_, title, body in decisions:
        slug = title.lower().replace(" ", "-")
        (root / "docs" / "decisions" / f"{id_}-{slug}.md").write_text(
            DECISION.format(id=id_, title=title, body=body)
        )
    for relative, text in (extra or {}).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (root / ".paper-trail.toml").write_text(
        "[paths]\n"
        'decisions = "docs/decisions"\n'
        'investigations = "docs/investigations"\n'
        'index = "docs/prd/index.md"\n'
        'adr = "docs/adr"\n'
        'specs = "docs/specs"\n'
        'plans = "docs/plans"\n'
        + ("cites = %r\n" % (list(cites),) if cites is not None else "")
        + (f'investigations_index = "{investigations_index}"\n' if investigations_index else "")
    )
    return _config.load(root)
