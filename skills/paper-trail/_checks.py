"""What can go wrong with a written record, as functions that find it.

Each check takes a Config and returns findings. None of them writes, and
none raises for a problem it is meant to report: a check that stops at
the first finding makes a person run it once per defect.
"""

import re
import subprocess
from urllib.parse import unquote
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import _docs
import _render
from _docs import Decision
from _config import Config, PaperTrailError

# [text](target), where the target may be wrapped in <> and may carry
# a title after it. Without the title branch a titled link matched
# nothing at all and went unchecked.
LINK = re.compile(r"\[[^\]]*\]\(\s*<([^>]*)>|\[[^\]]*\]\(\s*([^)\s]+)")

# CommonMark: a fence is three or more backticks or tildes, and only a
# closing fence of the same character and at least the same length ends
# it. Anything else is content.
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")

SPAN = re.compile(r"`[^`\n]*`")

# A path claim: backticked, with a directory separator and an extension.
# A bare `config.yaml` is a kind of file rather than a particular one.
PATHLIKE = re.compile(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]{1,5})`")

EXTERNAL = ("http://", "https://", "mailto:", "#")

# A rename hint only means something for a file named like a
# decision. Four leading characters of anything matched before.
NAMED_LIKE = re.compile(r"^\d{4}-")


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


def outside_fences(text: str) -> str:
    """The text with every fenced block blanked out.

    Blanked rather than removed so nothing shifts: a finding that named
    the wrong line would send someone to the wrong place. An unclosed
    fence runs to the end of the document, which is what CommonMark says
    and what a reader sees.
    """
    kept = []
    open_fence = None
    for line in text.split("\n"):
        found = FENCE.match(line)
        if found is None:
            kept.append("" if open_fence else line)
            continue
        marker = found.group(2)
        if open_fence is None:
            open_fence = marker
        elif (
            marker[0] == open_fence[0]
            and len(marker) >= len(open_fence)
            and not found.group(3).strip()
        ):
            open_fence = None
        kept.append("")
    return "\n".join(kept)


def prose(text: str) -> str:
    """The text with fenced blocks and code spans blanked out."""
    return "\n".join(
        SPAN.sub(lambda match: " " * len(match.group()), line)
        for line in outside_fences(text).split("\n")
    )


def _where(path: Path, config: Config) -> str:
    try:
        return str(path.relative_to(config.root))
    except ValueError:  # not covered: a path outside the root, which the config forbids
        return str(path)


def index_is_current(config: Config) -> list[Finding]:
    """The whole answer to a status two places would have to agree on."""
    wanted = _render.render(_docs.decisions(config), root=config.root, index=config.index)
    found = _docs.read(config.index) if config.index.is_file() else ""
    if found == wanted:
        return []
    return [Finding(where=_where(config.index, config), what="is not what the decisions say. Run index.py.")]


def readable(config: Config) -> tuple[list[Decision], list[Finding]]:
    """The decisions that parse, and a finding for each that does not.

    One run lists everything wrong. Reading the directory as a whole
    stops at the first bad file, which makes a person run the checks once
    per defect and quietly abandons every other check in the same pass.
    """
    good: list[Decision] = []
    findings: list[Finding] = []
    try:
        listed = sorted(path for path in config.decisions.iterdir() if path.suffix == ".md")
    except FileNotFoundError:
        return [], []
    except OSError as broken:
        return [], [
            Finding(where=_where(config.decisions, config), what=f"cannot be read: {broken}")
        ]

    for path in listed:
        try:
            good.extend(_docs.decisions_in(config, [path]))
        except PaperTrailError as broken:
            findings.append(Finding(where=_where(path, config), what=_without(str(broken), path)))
    return good, findings


def _without(message: str, path: Path) -> str:
    """The message without the absolute path in front of it.

    Every other finding is repo-relative, and `where` already carries it.
    """
    prefix = f"{path}: "
    return message[len(prefix) :] if message.startswith(prefix) else message


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
    moved_to = {item.id: item.path for item in readable(config)[0]}
    findings = []
    for path in markdown_files(config):
        for bracketed, bare in LINK.findall(prose(_docs.read(path))):
            target = bracketed or bare
            if target.startswith(EXTERNAL):
                continue
            name, _, _anchor = target.partition("#")
            if not name:
                continue
            # A link is URL-encoded, so a space arrives as %20 and a
            # literal lookup would always miss.
            name = unquote(name)
            # A leading slash means the repo root, not the filesystem's.
            against = config.root if name.startswith("/") else path.parent
            if (against / name.lstrip("/")).exists():
                continue
            stem = Path(name).stem
            moved = moved_to.get(stem[:4]) if NAMED_LIKE.match(stem) else None
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
        # Outside fences but not outside code spans: a path claim is
        # backticked by definition, and an example inside a fence is an
        # example rather than a claim.
        for claim in PATHLIKE.findall(outside_fences(_docs.read(path))):
            if "/" not in claim or claim.startswith(("./", "../")):
                continue
            if (config.root / claim).exists():
                continue
            findings.append(
                Finding(where=_where(path, config), what=f"names {claim}, which is not in the repo")
            )
    return findings


def _git_works(root: Path) -> bool:
    """Whether the binary is there, not just the directory.

    Every Windows checkout has a .git, and a minimal CI image without git
    is ordinary.
    """
    try:
        return (
            subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--git-dir"], capture_output=True
            ).returncode
            == 0
        )
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
