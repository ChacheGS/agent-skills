"""Write the index from the decision files, and the investigations and debt
indexes if the config names them.

Its own entry point rather than a flag on check.py, because writing and
checking are different jobs and a check that repairs what it is checking
can never fail.
"""

import argparse
import sys
from pathlib import Path

import _config
import _checks
import _docs
import _render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the indexes.")
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

    pages = [(config.index, text)]
    if config.investigations_index is not None:
        found, unreadable = _checks.readable_investigations(config)
        if unreadable:
            for finding in unreadable:
                print(finding, file=sys.stderr)
            return 1
        pages.append(
            (
                config.investigations_index,
                _render.render_investigations(
                    found, _docs.decisions(config), index=config.investigations_index
                ),
            )
        )
    if config.debt_index is not None:
        found, unreadable = _checks.readable_debt(config)
        if unreadable:
            for finding in unreadable:
                print(finding, file=sys.stderr)
            return 1
        pages.append(
            (
                config.debt_index,
                _render.render_debt(found, _docs.decisions(config), index=config.debt_index),
            )
        )

    for path, body in pages:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
