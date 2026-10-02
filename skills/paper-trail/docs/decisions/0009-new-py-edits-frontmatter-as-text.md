+++
id = "0009"
title = "new.py edits frontmatter as text"
status = "resolved"
opened = 2026-10-02
closed = 2026-10-02
conclusion = "supersede and close change one field at a time as text, because tomllib cannot write TOML back."
adr = []
spec = []
plan = []
+++

# new.py edits frontmatter as text

## What was decided

`new.py supersede` and `new.py close` set single fields by editing lines between the `+++` fences. A line starting `key =` is replaced, otherwise the field is added at the end of the frontmatter. The result is parsed again before the command returns.

## Why, and what it cost

Superseding and closing were hand edits across two files, and a typo only showed at the next check run. The standard library reads TOML and cannot write it, and a writer would drop the comments the templates carry for the next editor. Line edits keep them. The cost is that the edit knows only the simple `key = value` shape the templates write, so a multi-line value for one of these fields would break it. The re-parse makes that fail loudly.

## What was rejected, and why

Adding a TOML writing library. It would break the rule that the scripts have no dependencies.
