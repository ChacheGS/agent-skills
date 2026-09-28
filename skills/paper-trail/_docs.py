"""Reading the record: decisions, investigations, and the ADRs they cite.

TOML frontmatter rather than YAML because there is no YAML parser in the
standard library and hand-rolling one is how prose gets eaten. ADRs that
predate an adoption keep their YAML, and the reader at the bottom takes
only the shape they actually use and refuses the rest.
"""

import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from _config import Config, PaperTrailError

FENCE = "+++"

STATUSES = frozenset({"open", "resolved", "rejected", "superseded"})

NAMED = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*$")


def frontmatter(text: str) -> tuple[dict, str]:
    """The TOML block between +++ fences, and everything after it."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != FENCE:
        raise PaperTrailError(f"no {FENCE} frontmatter on the first line")
    try:
        end = lines.index(FENCE, 1)
    except ValueError:
        raise PaperTrailError(f"the {FENCE} frontmatter is never closed") from None
    try:
        fields = tomllib.loads("\n".join(lines[1:end]))
    except tomllib.TOMLDecodeError as broken:
        raise PaperTrailError(f"the frontmatter is not valid TOML: {broken}") from None
    return fields, "\n".join(lines[end + 1 :])


@dataclass(frozen=True)
class Decision:
    id: str
    title: str
    status: str
    opened: date
    closed: date | None
    conclusion: str
    adr: tuple[str, ...]
    spec: tuple[str, ...]
    plan: tuple[str, ...]
    superseded_by: str | None
    path: Path
    body: str


def decisions(config: Config) -> list[Decision]:
    """Every decision, by id, or a refusal naming what is wrong.

    A missing directory is empty rather than an error: a repo that has
    adopted the skill and not written a decision yet is a normal state.
    """
    if not config.decisions.is_dir():
        return []

    found: dict[str, Decision] = {}
    for path in sorted(config.decisions.glob("*.md")):
        named = NAMED.match(path.stem)
        if named is None:
            raise PaperTrailError(
                f"{path.name} is not named NNNN-slug.md, so nothing can link to it by id"
            )
        try:
            fields, body = frontmatter(path.read_text())
        except PaperTrailError as broken:
            raise PaperTrailError(f"{path}: {broken}") from None

        item = _decision(path=path, fields=fields, body=body)
        if named.group(1) != item.id:
            raise PaperTrailError(
                f"{path.name} starts with {named.group(1)} and its frontmatter says "
                f"{item.id}. The filename is what a link resolves against."
            )
        seen = found.get(item.id)
        if seen is not None:
            raise PaperTrailError(
                f"{seen.path.name} and {path.name} share the id {item.id}, so a link "
                f"to it points at whichever sorted first"
            )
        found[item.id] = item
    return [found[key] for key in sorted(found)]


def _decision(*, path: Path, fields: dict, body: str) -> Decision:
    for required in ("id", "title", "status", "opened", "conclusion"):
        if required not in fields:
            raise PaperTrailError(f"{path}: frontmatter has no {required}")
    status = fields["status"]
    if status not in STATUSES:
        raise PaperTrailError(
            f"{path}: status {status!r} is not one of {', '.join(sorted(STATUSES))}"
        )
    if status == "superseded" and not fields.get("superseded_by"):
        raise PaperTrailError(f"{path}: superseded by nothing, so the trail stops here")
    return Decision(
        id=str(fields["id"]),
        title=str(fields["title"]),
        status=status,
        opened=fields["opened"],
        closed=fields.get("closed"),
        conclusion=str(fields["conclusion"]),
        adr=tuple(fields.get("adr", ())),
        spec=tuple(fields.get("spec", ())),
        plan=tuple(fields.get("plan", ())),
        superseded_by=fields.get("superseded_by"),
        path=path,
        body=body,
    )


def adr_relations(path: Path) -> tuple[str, ...]:
    """What an ADR's YAML frontmatter says it is related to.

    ADRs predate an adoption and are not rewritten for it, so this reads
    the one shape they use: `related:` followed by indented `- ` items.
    Anything else is refused rather than guessed at, because a reader
    that quietly returned () would report every ADR as citing nothing.
    """
    lines = path.read_text().split("\n")
    if not lines or lines[0].strip() != "---":
        return ()
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise PaperTrailError(f"{path}: the --- frontmatter is never closed") from None

    related: list[str] = []
    collecting = False
    for line in lines[1:end]:
        if not line.strip():
            continue
        if collecting and line.startswith((" ", "\t")):
            item = line.strip()
            if not item.startswith("- "):
                raise PaperTrailError(f"{path}: cannot read {item!r} under related:")
            # A trailing comment is not part of the path: real ADRs
            # carry them, and reading one would report a file nobody
            # named.
            related.append(item[2:].split("#")[0].strip())
            continue
        collecting = False
        key, separator, value = line.partition(":")
        if not separator:
            raise PaperTrailError(f"{path}: cannot read frontmatter line {line!r}")
        if key.strip() == "related":
            rest = value.strip()
            if rest == "":
                collecting = True
                continue
            if rest == "[]":
                continue
            raise PaperTrailError(f"{path}: cannot read related: {rest!r}")
    return tuple(related)
