+++
id = "0002"
title = "A gap in migrated history is a finding, not a refusal"
status = "resolved"
opened = 2026-09-28
closed = 2026-09-28
conclusion = "Where old history may not know a fact, the check reports the gap and the file still loads."
adr = []
spec = []
plan = []
+++

# A gap in migrated history is a finding, not a refusal

## What was decided

A closed decision with no closing date, and an investigation with no frontmatter, do not stop the run. The first is a finding. The second is a note.

## Why, and what it cost

Refusing the file hides every other problem behind it and makes a person run the checks once per defect. A date invented to satisfy a parser is worse than a gap someone can see. The cost is that a record can pass with known holes, which is why notes are printed on every run.
