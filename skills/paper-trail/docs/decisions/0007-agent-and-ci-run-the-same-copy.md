+++
id = "0007"
title = "The agent and CI run the same copy of the scripts"
status = "resolved"
opened = 2026-10-02
closed = 2026-10-02
conclusion = "A repo that vendors the scripts names where, and check.py says so when it ran from anywhere else."
adr = []
spec = []
plan = []
+++

# The agent and CI run the same copy of the scripts

## What was decided

In vendored mode a config may set `paths.scripts` to the directory holding the repo's copy. When `check.py` runs from a different directory, it prints a note naming both. The adoption steps also tell the repo's agent file where the copy is, so an agent without the skill installed can find it.

## Why, and what it cost

An installed skill and a vendored copy can be different ages. If the agent runs the newer one and CI runs the older, a record passes locally and fails in CI. A vendored copy is also invisible to an agent that has never been told it exists. The cost is one more config key, and a note that only a vendored repo ever sees.

## What was rejected, and why

Dropping the vendored mode so the skill always owns the scripts. CI and contributors without the skill still need to run the checks, and requiring an install first would make the record depend on a tool the repo does not control.
