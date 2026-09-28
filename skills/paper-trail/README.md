# Adopting paper-trail

Three scripts, no dependencies, Python 3.11 or newer. 3.11 is the floor
because the config is TOML and `tomllib` arrives there: Debian 12 and
Ubuntu 24.04 are fine, RHEL 9's system Python is 3.9 and is not.

## 1. Choose where the scripts live

**Vendored**, the usual choice: copy `check.py`, `index.py`, `new.py`,
`_config.py`, `_docs.py`, `_checks.py`, `_render.py`, `VERSION` and
`templates/` into your repo and commit them. Your checks then run in CI
and for a contributor who has never installed this skill. `check.py`
compares `skill_version` in your config against the `VERSION` it was
copied with and says when the two have parted.

**Referenced**: leave them here and point at them. Nothing drifts, and
nothing runs where this skill is absent.

The tests do not need copying. They belong to this repo's own gate.

## 2. Write the config

`python3 new.py --root /path/to/your/repo --config` writes a starting
`.paper-trail.toml`. Edit the paths to match your layout; every key
under `[paths]` is required, and an unknown one is refused rather than
ignored, because a typo would leave the real key at its default and
check nothing.

## 3. Run the checks wherever your repo runs checks

```
python3 tools/paper-trail/check.py --root .
```

- **0** the record checks out
- **1** findings, one per line, each naming the file and what is wrong
- **2** it could not run: no config, or a config it cannot read

That distinction is the contract. Only one of those should stop a build.

## If you already have a table of decisions

Splitting it into files is a one-time job, and the parser is not worth
shipping for something that happens once. Write the split however you
like, and prove it with the assertion rather than by reading the diff:

- the set of titles round-trips exactly, and
- every body is byte-identical to its source cell, modulo leading and
  trailing whitespace.

Escape any pipes inside code spans before you start. A table row
carrying a bare `|` parses with extra columns, and a splitter that tries
to recover from that is how prose gets eaten silently.
