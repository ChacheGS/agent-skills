"""One screen of where the record stands.

For an agent starting a session or a person picking a repo back up: what
is open, what is in flight, what is owed. It reads the same files the
indexes do and writes nothing. It is not the checks; run check.py for
whether the record is true.
"""

import argparse
import sys
from pathlib import Path

import _checks
import _config
import _render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show what is open in the record.")
    parser.add_argument("--root", default=".", help="the repository root")
    args = parser.parse_args(argv)

    try:
        config = _config.load(Path(args.root))
    except _config.PaperTrailError as refusal:
        print(refusal, file=sys.stderr)
        return 2

    decisions, bad = _checks.readable(config)
    investigations, more = _checks.readable_investigations(config)
    debt, worse = _checks.readable_debt(config)

    open_decisions = [item for item in decisions if item.status == "open"]
    print(f"decisions: {len(open_decisions)} open, {len(decisions) - len(open_decisions)} settled")
    for item in open_decisions:
        print(f"  {item.id} {item.title}")

    live = [item for item in investigations if item.answered is None]
    print(f"investigations: {len(live)} open")
    for item in live:
        step = _render.next_step(item.body)
        print(f"  {item.id} {item.title}" + (f", next: {step}" if step else ""))

    if config.debt is not None:
        owed = [item for item in debt if item.resolved is None]
        print(f"debt: {len(owed)} open")
        for item in owed:
            print(f"  {item.id} {item.title}, repay when: {item.repay_when}")

    unreadable = len(bad) + len(more) + len(worse)
    if unreadable:
        print(f"{unreadable} file(s) do not parse and are left out. Run check.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
