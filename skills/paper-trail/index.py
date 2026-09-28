"""Write the index from the decision files.

Its own entry point rather than a flag on check.py, because writing and
checking are different jobs and a check that repairs what it is checking
can never fail.
"""

import argparse
import sys
from pathlib import Path

import _config
import _docs
import _render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the decision index.")
    parser.add_argument("--root", default=".", help="the repository root")
    args = parser.parse_args(argv)

    try:
        config = _config.load(Path(args.root))
    except _config.PaperTrailError as refusal:
        print(refusal, file=sys.stderr)
        return 2
    try:
        text = _render.render(_docs.decisions(config), root=config.root, index=config.index)
    except _config.PaperTrailError as broken:
        # A decision that will not parse is a problem with the record, and
        # writing an index that silently left it out would hide it.
        print(broken, file=sys.stderr)
        return 1

    config.index.parent.mkdir(parents=True, exist_ok=True)
    config.index.write_text(text, encoding="utf-8")
    print(f"wrote {config.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
