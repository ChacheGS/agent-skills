"""What can go wrong with a written record, as functions that find it.

Each check takes a Config and returns findings. None of them writes, and
none raises for a problem it is meant to report: a check that stops at
the first finding makes a person run it once per defect.
"""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import _docs
import _render
from _config import Config

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

FENCE = re.compile(r"^\s*```")

SPAN = re.compile(r"`[^`\n]*`")

# A path claim: backticked, with a directory separator and an extension.
# A bare `config.yaml` is a kind of file rather than a particular one.
PATHLIKE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]{1,5})`")

EXTERNAL = ("http://", "https://", "mailto:", "#")


@dataclass(frozen=True)
class Finding:
    where: str
    what: str

    def __str__(self) -> str:
        return f"{self.where}: {self.what}"


def markdown_files(config: Config) -> list[Path]:
    """Every markdown file in the record, in a stable order."""
    directories = (
        config.decisions,
        config.investigations,
        config.adr,
        config.specs,
        config.plans,
    )
    return sorted(
        path for directory in directories if directory.is_dir() for path in directory.rglob("*.md")
    )


def prose(text: str) -> str:
    """The text with fenced blocks and code spans blanked out.

    Blanked rather than removed so nothing shifts: a finding that named
    the wrong line would send someone to the wrong place.
    """
    kept = []
    inside = False
    for line in text.split("\n"):
        if FENCE.match(line):
            inside = not inside
            kept.append("")
            continue
        kept.append("" if inside else SPAN.sub(lambda match: " " * len(match.group()), line))
    return "\n".join(kept)


def _where(path: Path, config: Config) -> str:
    try:
        return str(path.relative_to(config.root))
    except ValueError:  # not covered: a path outside the root, which the config forbids
        return str(path)


def index_is_current(config: Config) -> list[Finding]:
    """The whole answer to a status two places would have to agree on."""
    wanted = _render.render(_docs.decisions(config), root=config.root, index=config.index)
    found = config.index.read_text() if config.index.is_file() else ""
    if found == wanted:
        return []
    return [Finding(where=_where(config.index, config), what="is not what the decisions say. Run index.py.")]


def links_resolve(config: Config) -> list[Finding]:
    """Every relative link in the record points at something."""
    moved_to = {item.id: item.path for item in _docs.decisions(config)}
    findings = []
    for path in markdown_files(config):
        for target in LINK.findall(prose(path.read_text())):
            if target.startswith(EXTERNAL):
                continue
            name, _, _anchor = target.partition("#")
            if not name:
                continue
            if (path.parent / name).exists():
                continue
            moved = moved_to.get(Path(name).stem[:4])
            findings.append(
                Finding(
                    where=_where(path, config),
                    what=(
                        f"links to {name}, which is now {moved.name}"
                        if moved is not None
                        else f"links to {name}, which is not there"
                    ),
                )
            )
    return findings


def relations_exist(config: Config) -> list[Finding]:
    """A decision's adr/spec/plan, and an ADR's own related list."""
    findings = []
    for item in _docs.decisions(config):
        for related in item.adr + item.spec + item.plan:
            if not (config.root / related).exists():
                findings.append(
                    Finding(where=_where(item.path, config), what=f"cites {related}, which is not there")
                )
    if config.adr.is_dir():
        for path in sorted(config.adr.glob("*.md")):
            for related in _docs.adr_relations(path):
                if not (config.root / related).exists():
                    findings.append(
                        Finding(
                            where=_where(path, config),
                            what=f"is related to {related}, which is not there",
                        )
                    )
    return findings


def paths_exist(config: Config) -> list[Finding]:
    """A backticked repo path in the record must name a real file.

    This is what catches prose describing code that moved.
    """
    findings = []
    for path in markdown_files(config):
        for claim in PATHLIKE.findall(path.read_text()):
            if "/" not in claim or claim.startswith(("./", "../")):
                continue
            if (config.root / claim).exists():
                continue
            findings.append(
                Finding(where=_where(path, config), what=f"names {claim}, which is not in the repo")
            )
    return findings
