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

## Closing an investigation

An investigation is a working file: the symptom, the measurements, and
the theories that died. When it is answered, the conclusion somebody
needs later belongs in a decision, and this file keeps the hunt.

Say so in its frontmatter:

```toml
answered = 2026-09-29
decision = "0067"
```

Both, or neither. An answered investigation stops being reported as
stale, and its title stops being the only thing a reader sees - which
matters because a title is written when the question is open, and a file
called "whether X works is unproven" still says that months after X was
proven.

An investigation with no frontmatter at all is read as a note and left
out of these checks rather than reported as broken - the skill shipped
without reading investigations, so an existing one is not a defect. The
run says which files those are, so the exemption is visible and someone
can end it by adding the header.

## What a document is asked

A decision and an investigation describe what is, so a backticked path
in one has to name a real file. A spec and a plan are dated proposals:
naming a file they intend to write is their job, and holding them to the
present would report hundreds of things nobody got wrong. Links are
checked everywhere, because a link that does not resolve is broken
whenever it was written.

## What the checks cannot do

Nothing here finds an investigation that was never opened. The checks
find drift between things that are written down; a hunt that lives only
in someone's head is invisible to all of them. `new.py` being cheap is
the whole mitigation, and it depends on a person reaching for it.

Nothing here reads prose for truth either. A path check catches a record
naming a file that moved; it cannot catch a record whose sentences are
simply no longer true, a comment explaining a line a later commit
deleted, or a conclusion stated more confidently than what was measured.
Those need a reader. In one adopting repo a review found five comments
justifying code that no longer existed, and every check passed on all
five.

The path check also reads only decisions and investigations. Prose in
source files, test scenarios and READMEs is outside it, which is where
that same review found the stale ones.
