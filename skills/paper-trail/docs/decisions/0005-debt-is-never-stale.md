+++
id = "0005"
title = "Debt is never reported stale and must say when to repay it"
status = "resolved"
opened = 2026-10-02
closed = 2026-10-02
conclusion = "A debt entry needs a repay_when condition, and no age ever counts against it."
adr = []
spec = []
plan = []
+++

# Debt is never reported stale and must say when to repay it

## What was decided

Debt entries have a required `repay_when` field, a condition and never a date. An open entry still holding the template's placeholder is a finding at once. Staleness is not checked for debt.

## Why, and what it cost

Debt is meant to sit until its condition holds, so an age would only teach people to ignore the report. The condition is what lets an agent asked what to do next judge which entries are due. An entry that cannot name one is a wish, and a list of wishes is a backlog.
