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

VERSION_FILE = Path(__file__).resolve().parent / "VERSION"


def version() -> str:
    """The version beside these scripts, or nothing.

    Read when asked rather than at import, and absent rather than fatal:
    the README lists VERSION among the files to vendor, so a half-done
    copy is ordinary and deserves the "could not run" it is rather than a
    traceback before argparse has looked at the arguments.
    """
    try:
        return VERSION_FILE.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return ""

CHECKS = (
    _checks.index_is_current,
    _checks.closing_dates,
    _checks.links_resolve,
    _checks.relations_exist,
    _checks.paths_exist,
    _checks.conclusions_written,
    _checks.answered_investigations,
    _checks.citations_resolve,
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

    # Every file that will not parse, named one by one, before anything
    # that reads them all. A run that stopped at the first made a person
    # run the checks once per defect and quietly abandoned the rest.
    findings = _checks.readable(config)[1]
    skipped = None
    try:
        for check in CHECKS:
            findings.extend(check(config))
        stale, skipped = _checks.stale_investigations(config)
        findings.extend(stale)
    except _config.PaperTrailError as broken:
        # Something no single file owns, such as two sharing an id.
        findings.append(_checks.Finding(where="the record", what=str(broken)))

    if skipped:
        print(f"skipped: {skipped}")
    for finding in findings:
        print(finding)
    # After the findings and never counted: falling behind the skill, or
    # keeping a file the checks do not read, is news rather than a defect
    # in the record.
    for note in _checks.investigations_left_out(config):
        print(note)
    for note in _checks.stamp_is_current(config, version()):
        print(note)

    if findings:
        print(f"{len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("the record checks out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
