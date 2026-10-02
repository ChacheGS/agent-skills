"""Scaffold a decision, an investigation, a debt entry, or a repo's config,
and do the two edits people get wrong by hand: supersede and close.

Half the answer to the problem the checks cannot reach: nothing can find
an investigation that was never opened, so the only lever is making one
cheap enough to open at the moment the hunt starts.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import _config
import _docs

HERE = Path(__file__).resolve().parent

TEMPLATES = HERE / "templates"

UNWANTED = re.compile(r"[^a-z0-9]+")


def slug(title: str) -> str:
    """A filename from a title, cut at a word rather than through one.

    The cap keeps filenames manageable; cutting at the last dash keeps
    them guessable. A record titled "...is unproven" once became
    "...-is-unp.md", and prose elsewhere cited the untruncated name,
    which resolved to nothing.
    """
    whole = UNWANTED.sub("-", title.lower()).strip("-")
    if len(whole) <= 60:
        return whole
    cut = whole[:60]
    return (cut.rsplit("-", 1)[0] if "-" in cut else cut).strip("-")


def next_id(existing: list[str]) -> str:
    return f"{max((int(item) for item in existing), default=0) + 1:04d}"


def _write_config(root: Path) -> int:
    path = root / _config.CONFIG_NAME
    if path.exists():
        print(f"{path} already exists", file=sys.stderr)
        return 2
    version = (HERE / "VERSION").read_text(encoding="utf-8-sig").strip()
    template = (TEMPLATES / "config.toml").read_text(encoding="utf-8-sig")
    path.write_text(template.format(version=version), encoding="utf-8")
    print(path)
    return 0


def _directory(config: _config.Config, kind: str) -> Path:
    directory = {
        "decision": config.decisions,
        "investigation": config.investigations,
        "debt": config.debt,
    }[kind]
    if directory is None:
        raise _config.PaperTrailError(
            f"{config.root / _config.CONFIG_NAME} names no paths.{kind}, so there is "
            f"nowhere to put one"
        )
    return directory


def _create(config: _config.Config, kind: str, title: str) -> Path:
    directory = _directory(config, kind)
    existing = (
        [item.id for item in _docs.decisions(config)]
        if kind == "decision"
        else [
            path.stem[:4] for path in sorted(directory.glob("*.md")) if path.stem[:4].isdigit()
        ]
    )
    named = slug(title)
    if not named:
        # `0002-.md` is not a name the parser accepts, so writing one
        # would wedge the record exactly as a stray file does.
        raise _config.PaperTrailError(
            f"{title!r} leaves nothing to name a file with. Give it a few words."
        )
    identifier = next_id(existing)
    path = directory / f"{identifier}-{named}.md"
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (TEMPLATES / f"{kind}.md")
        .read_text(encoding="utf-8-sig")
        .format(id=identifier, title=title, today=date.today())
    )
    return path


def _set(path: Path, key: str, value: str, *, keep: bool = False) -> None:
    """Set one frontmatter field by editing the text.

    tomllib reads TOML and cannot write it, and a writer would drop the
    comments the templates carry. A line that starts `key =` is replaced
    (or kept, with keep), otherwise the field goes at the end of the
    frontmatter. See docs/decisions/0009.
    """
    lines = path.read_text(encoding="utf-8-sig").split("\n")
    end = lines.index(_docs.FENCE, 1)
    for number in range(1, end):
        if lines[number].startswith(f"{key} ="):
            if not keep:
                lines[number] = f"{key} = {value}"
            break
    else:
        lines.insert(end, f"{key} = {value}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _find(directory: Path, identifier: str, kind: str) -> Path:
    found = sorted(directory.glob(f"{identifier}-*.md")) if directory.is_dir() else []
    if len(found) != 1:
        raise _config.PaperTrailError(f"no single {kind} has the id {identifier!r}")
    return found[0]


def supersede(config: _config.Config, old_id: str, title: str) -> tuple[Path, Path]:
    """Start the decision that replaces `old_id` and mark the old one.

    The new file is written first and the old one edited second; the
    result is parsed again so a bad edit fails here and not at the next
    check run.
    """
    old = next((item for item in _docs.decisions(config) if item.id == old_id), None)
    if old is None:
        raise _config.PaperTrailError(f"no decision has the id {old_id!r}")
    if old.status == "superseded":
        raise _config.PaperTrailError(f"{old.path.name} is already superseded by {old.superseded_by}")
    new = _create(config, "decision", title)
    _set(old.path, "status", '"superseded"')
    _set(old.path, "closed", str(date.today()), keep=True)
    _set(old.path, "superseded_by", f'"{new.name[:4]}"')
    _docs.decisions(config)
    return old.path, new


def close(config: _config.Config, kind: str, identifier: str, decision: str | None) -> Path:
    """Mark an investigation answered, or a debt entry resolved."""
    path = _find(_directory(config, kind), identifier, kind)
    if kind == "investigation":
        if decision is None:
            raise _config.PaperTrailError(
                "an answered investigation names the decision that kept its conclusion: "
                "pass --decision NNNN"
            )
        if decision not in {item.id for item in _docs.decisions(config)}:
            raise _config.PaperTrailError(f"no decision has the id {decision!r}")
        if _docs.investigations_in([path])[0].answered is not None:
            raise _config.PaperTrailError(f"{path.name} is already answered")
        _set(path, "answered", str(date.today()))
        _set(path, "decision", f'"{decision}"')
        _docs.investigations_in([path])
    else:
        if decision is not None:
            raise _config.PaperTrailError("--decision is for investigations")
        if _docs.debt_in([path])[0].resolved is not None:
            raise _config.PaperTrailError(f"{path.name} is already resolved")
        _set(path, "resolved", str(date.today()))
        _docs.debt_in([path])
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Start a decision, an investigation or a debt entry, "
        "or supersede a decision, or close an investigation or debt entry."
    )
    parser.add_argument("--root", default=".", help="the repository root")
    parser.add_argument(
        "--config", action="store_true", help="write a starting .paper-trail.toml and stop"
    )
    parser.add_argument("--decision", help="with close investigation: the decision that kept the conclusion")
    parser.add_argument(
        "kind", nargs="?", choices=("decision", "investigation", "debt", "supersede", "close")
    )
    parser.add_argument(
        "words",
        nargs="*",
        help="a title; or, for supersede, OLD-ID then a title; or, for close, investigation|debt then ID",
    )
    args = parser.parse_args(argv)

    if args.config:
        return _write_config(Path(args.root))
    wanted = {"supersede": 2, "close": 2}.get(args.kind, 1)
    if not args.kind or len(args.words) != wanted:
        parser.error("say which kind and give it a title, or pass --config")
    if args.kind == "close" and args.words[0] not in ("investigation", "debt"):
        parser.error("close takes investigation or debt, then the id")

    try:
        config = _config.load(Path(args.root))
        if args.kind == "supersede":
            old, new = supersede(config, *args.words)
            print(f"{old.name} is now superseded by {new.name[:4]}")
            print(new)
        elif args.kind == "close":
            print(close(config, args.words[0], args.words[1], args.decision))
        else:
            print(_create(config, args.kind, args.words[0]))
    except _config.PaperTrailError as refusal:
        print(refusal, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
