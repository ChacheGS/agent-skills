+++
id = "0008"
title = "Citing something no longer live is a finding"
status = "resolved"
opened = 2026-10-02
closed = 2026-10-02
conclusion = "Code that cites a superseded decision, an answered investigation or resolved debt is reported, though the file still exists."
adr = []
spec = []
plan = []
+++

# Citing something no longer live is a finding

## What was decided

`citations_resolve` reports a cited id that exists but has moved on: a decision with `superseded_by`, an investigation with `answered`, a debt entry with `resolved`. The message names the successor where there is one.

## Why, and what it cost

The old check only asked whether the file existed, so a comment pointing at a superseded decision passed, and the explanation it relied on was no longer the current one. This is the same drift the skill exists to catch. The cost is some noise: a comment that cites an answered investigation for its history will be reported until it cites the decision instead, which is the intended fix.
