# Changelog

Each entry says what can turn a clean record into findings. Re-vendoring
is copying the files again and writing the new number into
`skill_version`. Run `index.py` afterwards, since an index you generated
with an older version may differ from the one this version writes.

## 1.9.0

Includes everything since 1.7.0. The 1.8.0 number was used while this
was still being built, so treat 1.9.0 as the first version with all of it.

New findings on a record that was clean before:
- A decision whose `superseded_by` names no decision.
- A decision that is not open and has no "What was decided" or "Why"
  section, or an empty one. Headings match by their first words.
- A decision that is not open and still has a `TO BE WRITTEN` line.
- With `cites` set: code citing a decision that was superseded, an
  investigation that was answered, or debt that was resolved.

The decision index now shows `superseded by NNNN` and `replaces NNNN`.
Regenerate it with `index.py`, or the index check reports it.

New, and off until you use them:
- Debt entries, with a required `repay_when`: set `debt` and `debt_index`
  under `[paths]`, then `new.py debt "A shortcut"`.
- An investigations index: set `investigations_index`.
- `scripts` under `[paths]`, for a vendored copy: `check.py` says when it
  ran from somewhere else.
- `new.py supersede` and `new.py close`.
- `status.py`, a new file to vendor.

## 1.7.0 and earlier

See the git history.
