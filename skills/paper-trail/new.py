"""Scaffold a decision, an investigation, or a repo's config.

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
    return UNWANTED.sub("-", title.lower()).strip("-")[:60]


def next_id(existing: list[str]) -> str:
    return f"{max((int(item) for item in existing), default=0) + 1:04d}"


def _write_config(root: Path) -> int:
    path = root / _config.CONFIG_NAME
    if path.exists():
        print(f"{path} already exists", file=sys.stderr)
        return 2
    version = (HERE / "VERSION").read_text().strip()
    path.write_text((TEMPLATES / "config.toml").read_text().format(version=version))
    print(path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start a decision or an investigation.")
    parser.add_argument("--root", default=".", help="the repository root")
    parser.add_argument(
        "--config", action="store_true", help="write a starting .paper-trail.toml and stop"
    )
    parser.add_argument("kind", nargs="?", choices=("decision", "investigation"))
    parser.add_argument("title", nargs="?", help="what it is about, in a few words")
    args = parser.parse_args(argv)

    if args.config:
        return _write_config(Path(args.root))
    if not args.kind or not args.title:
        parser.error("say which kind and give it a title, or pass --config")

    try:
        config = _config.load(Path(args.root))
        existing = (
            [item.id for item in _docs.decisions(config)]
            if args.kind == "decision"
            else [path.stem[:4] for path in sorted(config.investigations.glob("*.md"))]
        )
    except _config.PaperTrailError as refusal:
        print(refusal, file=sys.stderr)
        return 2

    directory = config.decisions if args.kind == "decision" else config.investigations
    identifier = next_id(existing)
    path = directory / f"{identifier}-{slug(args.title)}.md"
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (TEMPLATES / f"{args.kind}.md")
        .read_text()
        .format(id=identifier, title=args.title, today=date.today())
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
