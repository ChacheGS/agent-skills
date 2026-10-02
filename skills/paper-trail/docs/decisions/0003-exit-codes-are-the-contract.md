+++
id = "0003"
title = "Exit codes are the contract: 0 clean, 1 findings, 2 could not run"
status = "resolved"
opened = 2026-09-28
closed = 2026-09-28
conclusion = "Only a record problem may fail a build; a missing or unreadable config exits 2 so a caller can tell them apart."
adr = []
spec = []
plan = []
+++

# Exit codes are the contract: 0 clean, 1 findings, 2 could not run

## What was decided

`check.py` exits 0 when the record is clean, 1 when it has findings, and 2 when it could not run.

## Why, and what it cost

A repo with no config has no record to be wrong, and a broken config says nothing about the record. A caller must be able to stop the build on one and not the other. Findings print one per line, naming the file, so a person does not have to rerun to learn the next one.
