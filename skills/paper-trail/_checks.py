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
    found = config.index.read_text(encoding="utf-8-sig") if config.index.is_file() else ""
    if found == wanted:
        return []
    return [Finding(where=_where(config.index, config), what="is not what the decisions say. Run index.py.")]


def closing_dates(config: Config) -> list[Finding]:
    """A decision that stopped being open says when.

    A finding rather than a refusal, because migrated history often does
    not know: a date invented to satisfy a parser is worse than a gap
    somebody can see and fill.
    """
    return [
        Finding(
            where=_where(item.path, config),
            what=f"is {item.status} and nothing says when it closed",
        )
        for item in _docs.decisions(config)
        if item.status != "open" and item.closed is None
    ]


def links_resolve(config: Config) -> list[Finding]:
    """Every relative link in the record points at something."""
    moved_to = {item.id: item.path for item in _docs.decisions(config)}
    findings = []
    for path in markdown_files(config):
        for target in LINK.findall(prose(path.read_text(encoding="utf-8-sig"))):
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


def describing_now(config: Config) -> list[Path]:
    """The documents that describe what is, rather than what is intended.

    A spec and a plan are dated proposals: naming a file they mean to
    write is their job, and asking them whether it exists today turns a
    check into noise, which is how a check gets turned off. A decision
    and an investigation describe the present and are held to it.
    """
    return sorted(
        path
        for directory in (config.decisions, config.investigations)
        if directory.is_dir()
        for path in directory.rglob("*.md")
    )


def paths_exist(config: Config) -> list[Finding]:
    """A backticked repo path in the record must name a real file.

    This is what catches prose describing code that moved.
    """
    findings = []
    for path in describing_now(config):
        for claim in PATHLIKE.findall(path.read_text(encoding="utf-8-sig")):
            if "/" not in claim or claim.startswith(("./", "../")):
                continue
            if (config.root / claim).exists():
                continue
            findings.append(
                Finding(where=_where(path, config), what=f"names {claim}, which is not in the repo")
            )
    return findings


def _git_works(root: Path) -> bool:
    """Whether the binary is there, not just the directory."""
    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-dir"], capture_output=True
        ).returncode == 0
    except OSError:
        return False


def _last_touched(root: Path, path: Path) -> datetime | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%cI", "--", str(path)],
            capture_output=True,
            text=True,
        )
    except OSError:
        # git is not on PATH. A .git directory says nothing about that,
        # and every Windows checkout has one.
        return None
    if done.returncode != 0 or not done.stdout.strip():
        return None
    return datetime.fromisoformat(done.stdout.strip())


def stale_investigations(config: Config) -> tuple[list[Finding], str | None]:
    """An investigation nobody has touched is finished or abandoned.

    Returns its findings and, when it could not run, the reason. A
    repository is not a given: this has to work in an export with no
    history, and saying so beats either failing or lying.
    """
    if not (config.root / ".git").exists() or not _git_works(config.root):
        return [], "no git available here, so investigation staleness was not checked"
    if not config.investigations.is_dir():
        return [], None

    findings = []
    now = datetime.now(timezone.utc)
    for path in sorted(config.investigations.glob("*.md")):
        touched = _last_touched(config.root, path)
        if touched is None:
            # Never committed, so it is being written right now.
            continue
        days = (now - touched).days
        if days > config.investigation_days:
            findings.append(
                Finding(
                    where=_where(path, config),
                    what=(
                        f"has not been touched in {days} days. Either it finished and owes "
                        f"a decision, or it was abandoned and owes a deletion."
                    ),
                )
            )
    return findings, None


def stamp_is_current(config: Config, version: str) -> list[Finding]:
    """Whether the recorded version and the copied one still agree.

    Not drift from upstream, which a vendored copy structurally cannot
    see: it carries its own VERSION and has no way to reach the skill it
    came from. What this catches is a re-vendor that copied the scripts
    and forgot the config, or the reverse, which is easy to do because
    they are two steps.

    Reported rather than failed by the caller: a contributor mid-task
    should hear about it without being stopped by it.
    """
    if config.mode != "vendored" or not config.skill_version:
        return []
    if config.skill_version == version:
        return []
    return [
        Finding(
            where=".paper-trail.toml",
            what=f"was vendored from paper-trail {config.skill_version}; this one is {version}",
        )
    ]
