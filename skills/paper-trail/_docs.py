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

# What a template writes into a field somebody still owes. Checked for in
# a decision's conclusion and blanked in the investigations index.
PLACEHOLDER = "TO BE WRITTEN"

NAMED = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*$")


def read(path: Path) -> str:
    """A file from the record, as text.

    Always utf-8, never the locale's default: that is ascii in a
    C-locale container and cp1252 on Windows, and either one turns a
    degree sign into a crash. `utf-8-sig` drops a byte order mark, which
    Windows editors write and which otherwise reads as content and
    diagnoses the wrong problem.
    """
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as broken:
        raise PaperTrailError(f"{path} is not utf-8: {broken}") from None


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

    try:
        # iterdir rather than glob: glob swallows a PermissionError and
        # answers [], and an index rewritten from that empty answer
        # overwrites a populated one and reports success.
        listed = sorted(path for path in config.decisions.iterdir() if path.suffix == ".md")
    except OSError as broken:
        raise PaperTrailError(f"{config.decisions} cannot be read: {broken}") from None

    return decisions_in(config, listed)


def decisions_in(config: Config, listed: list[Path]) -> list[Decision]:
    """The decisions in exactly these files, by id."""
    found: dict[str, Decision] = {}
    for path in listed:
        named = NAMED.match(path.stem)
        if named is None:
            raise PaperTrailError(
                f"{path.name} is not named NNNN-slug.md, so nothing can link to it by id"
            )
        try:
            fields, body = frontmatter(read(path))
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
    for when in ("opened", "closed"):
        given = fields.get(when)
        if given is not None and not isinstance(given, date):
            raise PaperTrailError(
                f"{path}: {when} is {given!r}, which is not a date. TOML writes one "
                f"bare, as 2026-09-28, and quoting it makes it a string nothing can "
                f"compare."
            )
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


@dataclass(frozen=True)
class Investigation:
    id: str
    title: str
    opened: date
    answered: date | None
    decision: str | None
    path: Path
    body: str


def investigations(config: Config) -> list[Investigation]:
    """Every investigation, by id.

    Read far more loosely than a decision. An investigation is a working
    file, edited while something is still being chased, and refusing to
    parse one mid-hunt would make the checks the thing in the way. Only
    `answered` and `decision` are read beyond the header a template
    writes, and both are optional.
    """
    if not config.investigations.is_dir():
        return []

    listed = sorted(item for item in config.investigations.iterdir() if item.suffix == ".md")
    return investigations_in(listed)


def investigations_in(listed: list[Path]) -> list[Investigation]:
    """The investigations in exactly these files, by id."""
    found: dict[str, Investigation] = {}
    for path in listed:
        named = NAMED.match(path.stem)
        if named is None:
            raise PaperTrailError(
                f"{path.name} is not named NNNN-slug.md, so nothing can link to it by id"
            )
        try:
            fields, body = frontmatter(read(path))
        except PaperTrailError as broken:
            raise PaperTrailError(f"{path}: {broken}") from None

        for required in ("id", "title", "opened"):
            if required not in fields:
                raise PaperTrailError(f"{path}: frontmatter has no {required}")
        for when in ("opened", "answered"):
            given = fields.get(when)
            if given is not None and not isinstance(given, date):
                raise PaperTrailError(
                    f"{path}: {when} is {given!r}, which is not a date. TOML writes one "
                    f"bare, as 2026-09-28, and quoting it makes it a string nothing can "
                    f"compare."
                )
        item = Investigation(
            id=str(fields["id"]),
            title=str(fields["title"]),
            opened=fields["opened"],
            answered=fields.get("answered"),
            decision=(str(fields["decision"]) if fields.get("decision") else None),
            path=path,
            body=body,
        )
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


def adr_relations(path: Path) -> tuple[str, ...]:
    """What an ADR's YAML frontmatter says it is related to.

    ADRs predate an adoption and are not rewritten for it, so this reads
    the one shape they use: `related:` followed by indented `- ` items.
    Anything else is refused rather than guessed at, because a reader
    that quietly returned () would report every ADR as citing nothing.
    """
    lines = read(path).split("\n")
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
            value = item[2:].strip()
            # A comment starts at a # preceded by whitespace; a # inside a
            # filename does not. Real ADRs carry the first kind.
            value = value.split(" #")[0].rstrip()
            if value[:1] in ("[", "{", "&", "*"):
                raise PaperTrailError(f"{path}: cannot read {value!r} under related:")
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                # A quoted scalar is ordinary YAML, and keeping the quotes
                # makes the path a file nobody named.
                value = value[1:-1]
            related.append(value)
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
