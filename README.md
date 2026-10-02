# agent-skills

Skills for coding agents, one folder each under `skills/`.

## Install

```
npx skills add ChacheGS/agent-skills --list                    # see what is here
npx skills add ChacheGS/agent-skills --skill paper-trail       # this project
npx skills add ChacheGS/agent-skills --skill paper-trail -g    # every project
npx skills update                                              # later
```

Without Node, clone the repo and link or place a skill folder in
`~/.claude/skills/`, or in `.claude/skills/` inside one project.

## Skills

| Skill | What it does |
|---|---|
| [paper-trail](skills/paper-trail) | Keeps a project's decisions, investigations and debt addressable, with checks that fail when they drift. |

MIT licensed.
