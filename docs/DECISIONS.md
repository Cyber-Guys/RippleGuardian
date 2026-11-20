# Decision log

Append-only. Humans make decisions; agents may draft an entry, but it counts only once a human has approved it and it is merged.
To reverse a decision, add a new entry that supersedes it. Don't edit old entries.

**Format**
```
## D-00n · <short title>
- Date: YYYY-MM-DD HH:MM CET · Decided by: <human(s)>
- Status: accepted | superseded by D-00m
- Decision: <one or two sentences>
- Why: <the reason, ideally tied to a judging criterion or a contest rule>
- Alternatives considered: <briefly>
- Consequences: <what changes for tasks, scope, the policy>
```

---

## D-001 · Project direction
- Status: **pending**. Agents do not assume any project idea until this is accepted (`CLAUDE.md` §0).

## D-002 · UI framework (Python)
- Status: **pending** (`CLAUDE.md` §4).
