---
name: paper-trail
description: Use when a decision gets made, when a hunt spans more than one measurement, when a fact needs a home, or when documentation and code have drifted apart. Keeps a project's written record addressable and true, with checks that fail rather than advise.
---

# paper-trail

A project's written record is four kinds of thing, and the only question
that matters is which one you have.

| You have | It goes in | It leaves when |
|---|---|---|
| A conclusion somebody will need again | a decision file | never; it is superseded, not deleted |
| A hunt spanning more than one measurement | an investigation file | it concludes, becoming a decision |
| A decision that named and rejected a real alternative | an ADR, cited by the decision | never |
| The depth behind a change | a spec, cited by the decision | never |

A decision is `NNNN-slug.md` with TOML frontmatter. The number is its
address: links carry the whole filename so an editor can follow them, and
the number is what lets a retitled decision keep every link pointing at
it.

## One fact, one home

A claim that needs explaining lives in exactly one place, and everywhere
else points at it. Two copies of an explanation are two things to update,
and the one that gets missed reads as current.

This is the rule the checks enforce, and it is why the index is generated
rather than written: a status in two places is two places to be wrong.

## Evidence

- Semantics need the operation run. A route that exists, a `--help` flag,
  a type signature: these prove reachability, not behaviour.
- Contradicting a tool's own statement raises the bar rather than
  lowering it. Demonstrate it end to end, or believe the tool.
- A test double's behaviour is a claim about the platform. Point at the
  live assertion that checks it, or say in a comment that it is a guess.

## The scripts

- `python3 <here>/check.py --root .` runs every check. 0 clean, 1
  findings, 2 could not run.
- `python3 <here>/index.py --root .` rewrites the index.
- `python3 <here>/new.py --root . decision "A title"` starts one.
- `python3 <here>/new.py --root . investigation "A symptom"` starts one.
- `python3 <here>/new.py --root . --config` writes a starting config.

Where those run is the adopting repo's business. This skill names no
build system, no target and no hook.

## What the checks cannot do

Nothing here finds an investigation that was never opened. The checks
find drift between things that are written down; a hunt that lives only
in someone's head is invisible to all of them. `new.py` being cheap is
the whole mitigation, and it depends on a person reaching for it.
