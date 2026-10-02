+++
id = "0006"
title = "A vendored copy cannot see upstream, and does not pretend to"
status = "resolved"
opened = 2026-09-28
closed = 2026-09-28
conclusion = "skill_version records what was adopted; check.py reports a mismatch with the copy beside it, never with upstream."
adr = []
spec = []
plan = []
+++

# A vendored copy cannot see upstream, and does not pretend to

## What was decided

The config's `skill_version` is compared with the `VERSION` file beside the scripts. A difference is printed as a note and never counted as a finding.

## Why, and what it cost

A vendored copy carries its own VERSION, so it has no way to reach the skill it came from. What the stamp does catch is a half-finished re-vendor, where the scripts or the config were updated and not both. The cost is that falling behind upstream is invisible, and the README says so.
