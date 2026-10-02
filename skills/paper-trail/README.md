# Adopting paper-trail

Three scripts, no dependencies, Python 3.11 or newer. 3.11 is the floor
because the config is TOML and `tomllib` arrives there: Debian 12 and
Ubuntu 24.04 are fine, RHEL 9's system Python is 3.9 and is not.

## 1. Choose where the scripts live

**Vendored**, the usual choice: copy `check.py`, `index.py`, `new.py`,
`_config.py`, `_docs.py`, `_checks.py`, `_render.py`, `VERSION` and
`templates/` into your repo and commit them. Your checks then run in CI
and for a contributor who has never installed this skill.

A vendored copy cannot tell you that this skill has moved on, and
nothing here pretends otherwise: the copy carries its own `VERSION`, so
it has no way to see upstream. What `skill_version` in your config buys
is smaller and still worth having. It is the version you recorded when
you adopted, and `check.py` says so when it disagrees with the `VERSION`
sitting beside the scripts, which is what a half-finished re-vendor
looks like. Updating means copying the files again and writing the new
number down.

**Referenced**: leave them here and point at them. Nothing drifts, and
nothing runs where this skill is absent.

The tests do not need copying. They belong to this repo's own gate.

## 2. Write the config

`python3 new.py --root /path/to/your/repo --config` writes a starting
`.paper-trail.toml`. Edit the paths to match your layout; every key
under `[paths]` is required except those five, and an unknown one is
refused rather than ignored, because a typo would leave the real key
at its default and check nothing.

Five keys are optional. `investigations_index` is where `index.py` writes
a page listing every investigation, open or answered. Absent, no such
page is written or checked.

`debt` and `debt_index` turn on a third kind of record, shortcuts taken
on purpose, each with a `repay_when` condition. `debt` is the directory
and `debt_index` the generated page, which cannot sit inside it. Absent,
this repo keeps none and nothing is written or checked.

`scripts` is for a vendored copy: the directory holding it, such as
`tools/paper-trail`. When `check.py` runs from anywhere else it says so,
because an installed skill and a vendored copy of different ages can
disagree about the same record. A referenced config that sets it is
refused.

`cites` is a list of globs naming files outside the
record that point at a decision by id, as a code comment saying
`see docs/decisions/0066` does. Those citations are then checked to
still name something. Empty by default.

## 3. Run the checks wherever your repo runs checks

```
python3 tools/paper-trail/check.py --root .
```

- **0** the record checks out
- **1** findings, one per line, each naming the file and what is wrong
- **2** it could not run: no config, or a config it cannot read

That distinction is the contract. Only one of those should stop a build.

## 4. Tell your agent where the scripts are

A vendored copy is invisible to an agent that has never been told it
exists, and not every agent has the skill installed. Put a line in the
file your agent reads (`CLAUDE.md`, `AGENTS.md`):

```
After editing docs/, run `python3 tools/paper-trail/check.py --root .`
and `python3 tools/paper-trail/index.py --root .`.
```

Use your own path, and set `scripts` in the config to the same one. With
the skill installed as well, the agent should still run the vendored
copy, so that it and CI give the same answer.

## Where your record lives, and what git can answer about it

Nothing here needs the record to be in a repository, or the config to
sit at a repository root. The only question git is asked is how long an
investigation has sat untouched, and where it cannot be asked it is
skipped with a sentence saying so, never failed:

| Your layout | What happens |
|---|---|
| A repository, record tracked | staleness is checked |
| A subdirectory of a repository | checked; the root need not be the repository root |
| Repositories as children of a plain directory, config at the parent | skipped, with the reason |
| A repository whose `docs/` is gitignored or otherwise untracked | skipped, with the reason |
| No git installed at all | skipped, with the reason |

The untracked case is worth knowing about because it used to be silent:
every file read as never committed, so nothing was ever stale and
nothing said why. Every other check works the same in all five, because
none of them asks git anything.

## If you already have a table of decisions

Splitting it into files is a one-time job, and the parser is not worth
shipping for something that happens once. Write the split however you
like, and prove it with the assertion rather than by reading the diff:

- the set of titles round-trips exactly, and
- every body is byte-identical to its source cell, modulo leading and
  trailing whitespace.

Give each body a "What was decided" and a "Why" section: a closed
decision without them is reported, and a split table has neither unless
you write them.

Escape any pipes inside code spans before you start. A table row
carrying a bare `|` parses with extra columns, and a splitter that tries
to recover from that is how prose gets eaten silently.
