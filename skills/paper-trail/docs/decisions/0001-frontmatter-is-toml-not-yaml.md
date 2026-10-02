+++
id = "0001"
title = "Frontmatter is TOML, not YAML"
status = "resolved"
opened = 2026-09-28
closed = 2026-09-28
conclusion = "Records use +++ TOML frontmatter, because the standard library can parse it and cannot parse YAML."
adr = []
spec = []
plan = []
+++

# Frontmatter is TOML, not YAML

## What was decided

Decisions, investigations and debt carry TOML between `+++` fences.

## Why, and what it cost

The scripts have no dependencies, and Python ships a TOML parser but no YAML one. Writing a YAML reader by hand is how prose gets eaten. The cost is that ADRs from before an adoption keep their YAML, so `_docs.py` has a reader that takes the one shape they use and refuses the rest.

## What was rejected, and why

Vendoring a YAML library. It would break the rule that a copied skill runs where it lands.
