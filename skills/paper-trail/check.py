"""Every check, one line per finding.

Exit codes are the contract: 0 clean, 1 findings, 2 could not run. A
caller has to be able to tell "the record has a problem" from "nobody
told me where the record is", because only one of those should stop a
build.
"""

import argparse
import sys
from pathlib import Path

import _checks
import _config

VERSION = (Path(__file__).resolve().parent / "VERSION").read_text().strip()

CHECKS = (
    _checks.index_is_current,
    _checks.links_resolve,
    _checks.relations_exist,
    _checks.paths_exist,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the written record.")
    parser.add_argument("--root", default=".", help="the repository root")
    args = parser.parse_args(argv)

    try:
        config = _config.load(Path(args.root))
    except _config.PaperTrailError as refusal:
        # Nobody said where the record is, so nothing ran.
        print(refusal, file=sys.stderr)
        return 2

    findings = []
    skipped = None
    try:
        for check in CHECKS:
            findings.extend(check(config))
        stale, skipped = _checks.stale_investigations(config)
        findings.extend(stale)
    except _config.PaperTrailError as broken:
        # A decision file that will not parse is a problem with the record
        # rather than with the configuration. Every check reads the
        # decisions, so there is nothing further to run until it is fixed.
        findings.append(_checks.Finding(where="the record", what=str(broken)))

    if skipped:
        print(f"skipped: {skipped}")
    for finding in findings:
        print(finding)
    # After the findings and never counted: falling behind the skill is
    # news, not a defect in the record.
    for note in _checks.stamp_is_current(config, VERSION):
        print(note)

    if findings:
        print(f"{len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("the record checks out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
