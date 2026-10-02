---
name: paper-trail
description: Use when a decision gets made, when a hunt spans more than one measurement, when a fact needs a home, or when documentation and code have drifted apart. Keeps a project's written record addressable and true, with checks that fail rather than advise.
---

# paper-trail

A project's written record is five kinds of thing, and the only question
that matters is which one you have.

| You have | It goes in | It leaves when |
|---|---|---|
| A conclusion somebody will need again | a decision file | never; it is superseded, not deleted |
| A hunt spanning more than one measurement | an investigation file | it concludes, becoming a decision |
| A shortcut taken on purpose, with a cost | a debt file | it is paid back, which sets `resolved`; the file stays |
| A decision that named and rejected a real alternative | an ADR, cited by the decision | never |
| The depth behind a change | a spec, cited by the decision | never |

A decision is `NNNN-slug.md` with TOML frontmatter. The number is its
address: links carry the whole filename so an editor can follow them, and
the number is what lets a retitled decision keep every link pointing at
it.

## A decision's frontmatter

```toml
id = "0007"              # must match the filename
title = "..."
status = "open"          # open, resolved, rejected or superseded
opened = 2026-09-28      # a bare TOML date; quoted, it is a string
closed = 2026-10-02      # required once status is not open
conclusion = "One sentence, the thing a reader needs."
adr = []                 # repo-relative paths, each must exist
spec = []
plan = []
superseded_by = "0012"   # required when status is superseded
```

`conclusion` is what the index shows, so write it last and write it for
someone who will not open the file. `new.py` starts it as `TO BE
WRITTEN`, and a decision that has closed with that still in place is
reported.

A closed decision needs a "What was decided" and a "Why" section with
something in them. Headings are matched by their first words, so
"Why this way" counts. Open decisions are exempt.

The template leaves a `TO BE WRITTEN` line under "What was rejected".
Not every decision rejects something: fill it in, or delete the section.
A closed decision that keeps the stub is reported.

To supersede, run `new.py supersede OLD "New title"`, then `index.py`.
It sets `status`, `closed` and `superseded_by` on the old file for you;
by hand, those are the three fields. Leave the old file where it is. Its number is still
an address. Do not write "replaces" in the new file: the index derives it
from `superseded_by`, so the trail reads both ways from one copy.

## One fact, one home

A claim that needs explaining lives in exactly one place, and everywhere
else points at it. Two copies of an explanation are two things to update,
and the one that gets missed reads as current.

This is the rule the checks enforce, and it is why the index is generated
rather than written: a status in two places is two places to be wrong.

## The scripts

`<here>` is the directory holding these scripts. If the repo's config
sets `scripts`, or its `CLAUDE.md` or `AGENTS.md` names a copy, use that
copy even when this skill is installed: CI runs it, and two copies of
different ages can disagree. Otherwise `<here>` is where this skill is
installed. `--root` is the repo whose `.paper-trail.toml` says where the
record lives.

- `python3 <here>/check.py --root .` runs every check. 0 clean, 1
  findings, 2 could not run.
- `python3 <here>/status.py --root .` shows what is open: decisions,
  investigations with their next step, and debt with its `repay_when`.
  Run it first when picking up a repo. It writes nothing.
- `python3 <here>/index.py --root .` rewrites the index, and the
  investigations index if the config names one.
- `python3 <here>/new.py --root . decision "A title"` starts one.
- `python3 <here>/new.py --root . investigation "A symptom"` starts one.
- `python3 <here>/new.py --root . debt "A shortcut"` starts one, if the
  config names a `debt` directory.
- `python3 <here>/new.py --root . supersede 0004 "The new title"` starts the
  replacing decision and marks 0004 superseded.
- `python3 <here>/new.py --root . close investigation 0002 --decision 0007`
  marks an investigation answered. `close debt 0003` marks debt resolved.
- `python3 <here>/new.py --root . --config` writes a starting config.

Where those run is the adopting repo's business. This skill names no
build system, no target and no hook.

Run `check.py` after touching the record, and `index.py` after changing
any decision's status or conclusion. The index is generated, so a
hand-edit to it is a finding.

## What the checks report

- An index differs from what the files say.
- A decision or investigation that does not parse, or has a bad field.
- A decision that is not open and has no `closed` date, still has the
  placeholder conclusion, has no "What was decided" or "Why" section
  (or an empty one), or still has a `TO BE WRITTEN` line in its body.
- A link, an `adr`/`spec`/`plan` entry, or a `superseded_by` id that points
  at nothing.
- A backticked repo path in a decision or investigation that is not in
  the repo.
- An investigation untouched for longer than `investigation_days`
  (default 14, set under `[thresholds]`), unless it is answered.
- An investigation that is answered but names no decision, or the
  reverse.
- A debt entry that does not parse, has no `repay_when`, is still open
  with the template's `repay_when`, or names a decision that does not
  exist.
- A cited id that no longer exists, or that was superseded, answered or
  resolved (see "Code that cites the record").

Two things are printed but never counted as findings: a vendored copy
whose `VERSION` differs from the `skill_version` recorded in the config,
and investigations with no frontmatter, which are left out.

## Finding your bearings

The decision index lists what was settled and what is open. Set
`investigations_index` under `[paths]` and `index.py` also writes a page
of every investigation: the open ones with the first line of their
`## Next` section, and the answered ones with the decision that kept
the conclusion. Read it first when picking up a repo, to see what is in
flight. Absent, no such page is written or checked.

## Debt

A shortcut taken on purpose is not a defect to fix quietly. It is a
choice with a cost, and the record keeps it so nobody builds on it by
accident and so somebody can tell when it is due.

```toml
id = "0003"
title = "One global lock"
opened = 2026-10-02
repay_when = "a second writer exists"   # a condition, never a date
resolved = 2026-11-10                   # once paid; the file stays
decision = "0012"                       # optional: the decision that accepted it
```

`repay_when` is the field that matters. Asked "what do we do next", read
the open entries in the debt index: it states how many are open and each
one's condition, so judge which are due now rather than listing them all.
An entry that cannot name a condition is a wish and does not belong here.

Set `debt` and `debt_index` under `[paths]`. Absent, the repo keeps none
and nothing is written or checked. The index cannot sit inside `debt`,
where every file must be an entry. Code can cite an entry by id
(`docs/debt/0003`) and is checked like any other citation.

Nothing reports debt as stale. It is meant to sit until its condition
holds, and an age would only teach people to ignore the report.

## Closing an investigation

An investigation is a working file: the symptom, the measurements, and
the theories that died. When it is answered, the conclusion somebody
needs later belongs in a decision, and this file keeps the hunt.

Run `new.py close investigation ID --decision NNNN`, or say so in its
frontmatter:

```toml
answered = 2026-09-29
decision = "0067"
```

Both, or neither. An answered investigation stops being reported as
stale, and its title stops being the only thing a reader sees. That
matters because a title is written when the question is open, and a file
called "whether X works is unproven" still says that months after X was
proven.

An investigation with no frontmatter at all is read as a note and left
out of these checks rather than reported as broken, so an existing one
is not a defect. The run says which files those are, so the exemption is
visible and someone can end it by adding the header.

## What a document is asked

A decision and an investigation describe what is, so a backticked path
in one has to name a real file. A spec and a plan are dated proposals:
naming a file they intend to write is their job, and holding them to the
present would report hundreds of things nobody got wrong. Links are
checked everywhere, because a link that does not resolve is broken
whenever it was written.

## Code that cites the record

An explanation earns the right to live in one place by everywhere else
pointing at it, and a comment saying `see docs/decisions/0066` is that
pointer. It stops being true when the decision is renumbered, superseded
into a new file, or deleted, and nothing in the record can see that: the
citation lives in source the checks never read.

List the files that cite it and they get checked:

```toml
[paths]
cites = ["some/path/src/*.c", "some/other/path/*.js"]
```

Empty by default. Matched by id rather than by filename, because an id is
what a person writes and it survives the title being reworded. Only the
id is checked, so `docs/decisions/0066` and
`docs/decisions/0066-whatever-it-was-called.md` are both fine.

A citation that resolves is still reported when what it names has moved
on: a decision that was superseded, an investigation that was answered,
a debt entry that was resolved. Cite the successor, or the decision that
kept the conclusion, and delete a comment about debt that is paid.

## What the checks cannot do

Nothing here finds an investigation that was never opened. The checks
find drift between things that are written down; a hunt that lives only
in someone's head is invisible to all of them. `new.py` being cheap is
the whole mitigation, and it depends on a person reaching for it.

Nothing here reads prose for truth either. A path check catches a record
naming a file that moved; it cannot catch a record whose sentences are
simply no longer true, a comment explaining a line a later commit
deleted, or a conclusion stated more confidently than what was measured.
Those need a reader.

The path check also reads only decisions and investigations. Prose in
source files, tests and READMEs is outside it.
