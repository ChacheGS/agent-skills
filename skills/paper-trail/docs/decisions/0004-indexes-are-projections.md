+++
id = "0004"
title = "Indexes are generated from the files and never authored"
status = "resolved"
opened = 2026-09-28
closed = 2026-09-28
conclusion = "A status lives in one place, the file; every index is a view of it, and a check fails if one is stale."
adr = []
spec = []
plan = []
+++

# Indexes are generated from the files and never authored

## What was decided

`index.py` writes the decision index, and optionally the investigations and debt indexes. Nobody edits them. `check.py` reports one that differs from what the files say.

## Why, and what it cost

A status written in two places is two places to be wrong. The indexes show an opened date and never an age, because an age changes every day with no file changing, and the currency check would then fail on a clean record. The cost is one extra step after any status change.
