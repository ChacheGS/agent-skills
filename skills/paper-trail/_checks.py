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
        config.debt,
        config.adr,
        config.specs,
        config.plans,
    )
    return sorted(
        path
        for directory in directories
        if directory is not None and directory.is_dir()
        for path in directory.rglob("*.md")
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
    findings = []
    if found != wanted:
        findings.append(
            Finding(where=_where(config.index, config), what="is not what the decisions say. Run index.py.")
        )
    if config.investigations_index is not None:
        # Unparseable investigations are answered_investigations()'s
        # findings; reporting them here too would say each twice.
        wanted = _render.render_investigations(
            readable_investigations(config)[0],
            _docs.decisions(config),
            index=config.investigations_index,
        )
        found = (
            _docs.read(config.investigations_index)
            if config.investigations_index.is_file()
            else ""
        )
        if found != wanted:
            findings.append(
                Finding(
                    where=_where(config.investigations_index, config),
                    what="is not what the investigations say. Run index.py.",
                )
            )
    if config.debt_index is not None:
        wanted = _render.render_debt(
            readable_debt(config)[0], _docs.decisions(config), index=config.debt_index
        )
        found = _docs.read(config.debt_index) if config.debt_index.is_file() else ""
        if found != wanted:
            findings.append(
                Finding(
                    where=_where(config.debt_index, config),
                    what="is not what the debt files say. Run index.py.",
                )
            )
    return findings


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


def readable_investigations(config: Config) -> tuple[list, list[Finding]]:
    """The investigations that parse, and a finding for each that does not.

    Same shape and same reason as readable() above: one bad file names
    itself and the rest of the record is still checked.
    """
    good: list = []
    findings: list[Finding] = []
    if not config.investigations.is_dir():
        return [], []
    try:
        listed = sorted(
            path for path in config.investigations.iterdir() if path.suffix == ".md"
        )
    except OSError as broken:
        return [], [
            Finding(
                where=_where(config.investigations, config),
                what=f"cannot be read: {broken}",
            )
        ]

    for path in listed:
        if not _docs.read(path).startswith(_docs.FENCE):
            # No frontmatter at all is a note somebody keeps here, not a
            # malformed record. This check was added after the skill
            # shipped, and an adopter's existing files are not defects.
            # Said out loud by investigations_left_out() rather than
            # skipped in silence, because a file nobody knows is exempt
            # is a file nobody fixes.
            continue
        try:
            good.extend(_docs.investigations_in([path]))
        except PaperTrailError as broken:
            findings.append(
                Finding(where=_where(path, config), what=_without(str(broken), path))
            )
    return good, findings


def readable_debt(config: Config) -> tuple[list, list[Finding]]:
    """The debt entries that parse, and a finding for each that does not.

    Every .md file here is an entry. Unlike investigations there is no
    older record to be kind to, so a file without frontmatter is a defect.
    """
    if config.debt is None or not config.debt.is_dir():
        return [], []
    good: list = []
    findings: list[Finding] = []
    try:
        listed = sorted(path for path in config.debt.iterdir() if path.suffix == ".md")
    except OSError as broken:
        return [], [Finding(where=_where(config.debt, config), what=f"cannot be read: {broken}")]
    for path in listed:
        try:
            good.extend(_docs.debt_in([path]))
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
    somebody can see and fill. See docs/decisions/0002.
    """
    return [
        Finding(
            where=_where(item.path, config),
            what=f"is {item.status} and nothing says when it closed",
        )
        for item in _docs.decisions(config)
        if item.status != "open" and item.closed is None
    ]


def conclusions_written(config: Config) -> list[Finding]:
    """The conclusion field is what the index renders, not the body.

    A decision whose body says everything and whose conclusion is still
    the template's placeholder reads, from the index, as a decision that
    decided nothing - and the index is where somebody looks first.

    Only once it has stopped being open, for the same reason closing
    dates are: a decision written an hour ago and still being argued is
    allowed to have nothing settled in it yet. One that closed and never
    had its one line written is the defect.
    """
    return [
        Finding(
            where=_where(item.path, config),
            what="is {0} and still has the template's conclusion, which is what the index shows".format(
                item.status
            ),
        )
        for item in readable(config)[0]
        if item.status != "open" and _docs.PLACEHOLDER in item.conclusion
    ]


def stubs_left(config: Config) -> list[Finding]:
    """A closed decision still carrying a template stub in its body.

    The template leaves a marker line under "What was rejected" because
    not every decision rejects something. Filling it in and deleting the
    section both say so on purpose; leaving the marker says nobody
    decided. Only lines that start with the marker count, so prose
    mentioning it is fine, and only once closed, for the reason
    conclusions_written gives.
    """
    return [
        Finding(
            where=_where(item.path, config),
            what=f"is {item.status} and still has a {_docs.PLACEHOLDER} line. Fill it in, or delete the section.",
        )
        for item in readable(config)[0]
        if item.status != "open"
        and any(
            line.strip().startswith(_docs.PLACEHOLDER)
            for line in outside_fences(item.body).split("\n")
        )
    ]


def answered_investigations(config: Config) -> list[Finding]:
    """An investigation that finished names the decision that kept it.

    An investigation is a working file: the hunt, the measurements, the
    theories that died. The conclusion somebody needs later belongs in a
    decision, and this is the check that says so out loud rather than
    leaving a closed investigation looking open forever because its title
    is still the question it was opened with.
    """
    known = {item.id for item in readable(config)[0]}
    found, findings = readable_investigations(config)
    for item in found:
        if item.answered is None:
            if item.decision is not None:
                findings.append(
                    Finding(
                        where=_where(item.path, config),
                        what=(
                            f"names decision {item.decision} but nothing says when it "
                            f"was answered"
                        ),
                    )
                )
            continue
        if item.decision is None:
            findings.append(
                Finding(
                    where=_where(item.path, config),
                    what=(
                        "was answered and names no decision, so its conclusion lives "
                        "only in a file titled as an open question"
                    ),
                )
            )
        elif item.decision not in known:
            findings.append(
                Finding(
                    where=_where(item.path, config),
                    what=f"names decision {item.decision}, which does not exist",
                )
            )
    return findings


def debt_is_sound(config: Config) -> list[Finding]:
    """Open debt says when to pay it, and a named decision exists.

    The point of the list is the repay_when line: an agent asked what to
    do next reads it to judge which entries are due. One still holding
    the template's placeholder tells it nothing, so it is a finding
    straight away, not only once closed as a conclusion is. See
    docs/decisions/0005.
    """
    good, findings = readable_debt(config)
    known = {item.id for item in readable(config)[0]}
    for item in good:
        if item.resolved is None and _docs.PLACEHOLDER in item.repay_when:
            findings.append(
                Finding(
                    where=_where(item.path, config),
                    what="is open and still has the template's repay_when, which is what the debt index shows",
                )
            )
        if item.decision is not None and item.decision not in known:
            findings.append(
                Finding(
                    where=_where(item.path, config),
                    what=f"names decision {item.decision}, which does not exist",
                )
            )
    return findings


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
    """A decision's adr/spec/plan and superseded_by, and an ADR's own related list."""
    findings = []
    decisions = _docs.decisions(config)
    known = {item.id for item in decisions}
    for item in decisions:
        if item.superseded_by and str(item.superseded_by) not in known:
            findings.append(
                Finding(
                    where=_where(item.path, config),
                    what=f"is superseded by {item.superseded_by}, which does not exist",
                )
            )
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
        for directory in (config.decisions, config.investigations, config.debt)
        if directory is not None and directory.is_dir()
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


def _git(root: Path, *args: str) -> subprocess.CompletedProcess | None:
    """Run git here, or None if there is no git to run.

    A missing binary and a directory that is not in a repository are the
    same answer to the caller: the question cannot be asked.
    """
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True
        )
    except OSError:
        return None


def _in_a_repository(root: Path) -> bool:
    """Ask git rather than looking for a .git beside the config.

    The record is often not at the repository root, and a repository is
    often not where the record is: a directory holding several repos as
    children has no .git of its own, and a subdirectory of a repo has no
    .git either. Looking for the directory answered no to both.
    """
    done = _git(root, "rev-parse", "--git-dir")
    return done is not None and done.returncode == 0


def _tracked(root: Path, directory: Path) -> bool:
    """Whether git knows about anything in here at all.

    A record kept out of git, by .gitignore or by living in a directory
    nobody shares, makes every file read as never committed. Silently
    exempting it from staleness is worse than saying the question cannot
    be answered.
    """
    done = _git(root, "ls-files", "--", str(directory))
    return done is not None and done.returncode == 0 and bool(done.stdout.strip())


def _last_touched(root: Path, path: Path) -> datetime | None:
    done = _git(root, "log", "-1", "--format=%cI", "--", str(path))
    if done is None or done.returncode != 0 or not done.stdout.strip():
        return None
    return datetime.fromisoformat(done.stdout.strip())


def stale_investigations(config: Config) -> tuple[list[Finding], str | None]:
    """An investigation nobody has touched is finished or abandoned.

    Returns its findings and, when it could not run, the reason. A
    repository is not a given: this has to work in an export with no
    history, and saying so beats either failing or lying.
    """
    if not _in_a_repository(config.root):
        return [], "no git repository here, so investigation staleness was not checked"
    if not config.investigations.is_dir():
        return [], None
    if any(config.investigations.glob("*.md")) and not _tracked(
        config.root, config.investigations
    ):
        return [], (
            f"{_where(config.investigations, config)} is not tracked by git, so "
            f"investigation staleness was not checked"
        )

    # An unreadable file is readable_investigations()'s finding to make,
    # not a reason to skip staleness for every other investigation.
    answered = {
        item.path for item in readable_investigations(config)[0] if item.answered is not None
    }

    findings = []
    now = datetime.now(timezone.utc)
    for path in sorted(config.investigations.glob("*.md")):
        if path in answered:
            # Finished on purpose, and kept for its refuted list.
            continue
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


def _cited_ids(config: Config) -> dict[str, set[str]]:
    """The ids that exist, by the directory a citation would name."""
    ids = {}
    for directory, found in (
        (config.decisions, [item.id for item in readable(config)[0]]),
        (config.investigations, [item.id for item in readable_investigations(config)[0]]),
        (config.debt, [item.id for item in readable_debt(config)[0]]),
    ):
        if directory is None:
            continue
        try:
            where = directory.relative_to(config.root).as_posix()
        except ValueError:
            continue
        ids[where] = set(found)
    return ids


def citations_resolve(config: Config) -> list[Finding]:
    """Code that points at a decision by id still points at one.

    The record's own links are checked by links_resolve; this is the
    other direction, and the one that rots unwatched. A comment saying
    "see docs/decisions/0004" is how an explanation earns the right to
    live in exactly one place, and it stops being true the moment that
    decision is renumbered, superseded into a new file, or deleted.

    Only the globs the repo lists under paths.cites, because only it
    knows which of its sources cite the record. Matched by id rather than
    by filename: an id is what a person writes, and it survives a title
    being reworded.
    """
    known = _cited_ids(config)
    if not config.cites or not known:
        return []

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(where) for where in sorted(known)) + r")/(\d{4})"
    )
    findings = []
    for glob in config.cites:
        for path in sorted(config.root.glob(glob)):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError as broken:
                findings.append(
                    Finding(where=_where(path, config), what=f"cannot be read: {broken}")
                )
                continue
            for where, cited in dict.fromkeys(pattern.findall(text)):
                if cited not in known[where]:
                    findings.append(
                        Finding(
                            where=_where(path, config),
                            what=f"cites {where}/{cited}, which does not exist",
                        )
                    )
    return findings


def investigations_left_out(config: Config) -> list[Finding]:
    """Investigations with no frontmatter, named rather than skipped quietly.

    A note, not a finding: these are ordinary in a record older than the
    fields, and stopping a build over one would be the skill getting in
    the way of the work it exists to support. Saying so is what turns an
    exemption somebody does not know about into one they can act on.
    """
    if not config.investigations.is_dir():
        return []
    try:
        listed = sorted(
            path for path in config.investigations.iterdir() if path.suffix == ".md"
        )
    except OSError:
        # readable_investigations() reports this as a finding; a note
        # saying the same thing twice helps nobody.
        return []
    return [
        Finding(
            where=_where(path, config),
            what=(
                "has no +++ frontmatter, so it is read as a note and left out of the "
                "investigation checks. Add id, title and opened to include it."
            ),
        )
        for path in listed
        if not _docs.read(path).startswith(_docs.FENCE)
    ]


def stamp_is_current(config: Config, version: str) -> list[Finding]:
    """Whether the recorded version and the copied one still agree.

    Not drift from upstream, which a vendored copy structurally cannot
    see: it carries its own VERSION and has no way to reach the skill it
    came from. What this catches is a re-vendor that copied the scripts
    and forgot the config, or the reverse, which is easy to do because
    they are two steps.

    Reported rather than failed by the caller: a contributor mid-task
    should hear about it without being stopped by it. See
    docs/decisions/0006.
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
