---
name: decisions
description: Archive, classify and audit the decisions of a mid/long-term project (decision → pack → iteration, 4 states, justified hash-chained journal). Use when the user makes, changes, validates or asks about a decision, asks what to do next or where things stand, or wants an existing project's history turned into a decision registry.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/dec.py *)
---

# Decisions

CLI: `python3 ${CLAUDE_SKILL_DIR}/scripts/dec.py <cmd>` (below: `D <cmd>`). `D -h` lists commands, `D <cmd> -h` their options. Data lives in `<project>/.decisions/`: never read or edit its files by hand.

## Language
- Reply, and write **everything the user will read** (titles, questions, reasons, documents, tables, summaries) in **the user's language**, i.e. the language they write in. CLI flags, ids and state keys stay as they are.
- `D init --lang <ISO code>` stores the project language in `.decisions/config.json`; script messages and generated document labels follow it. Shipped catalogs: `en`, `fr`.
- Other language: when the script says "No catalog for language…", translate `${CLAUDE_SKILL_DIR}/i18n/en.json` once into `.decisions/i18n/<code>.json` (same keys, same `<placeholders>` and `{braces}`), and relay script output in the user's language until then.
- If the user's language differs from the project's, ask once whether to switch (`D config lang <code>`).

## Model
- **Decision** (Cn): settles ONE question; linked to a document (created or appended automatically); states `todo < doing < done < validated`.
- **Pack**: group of related decisions, at most `max_pack` (default 6). When full, new decisions go automatically to an overflow pack "Title (2)". State = lowest of its decisions (computed).
- **Iteration**: cycle of packs; state = lowest of its packs. A new one opens only when the previous is Validated.
- Index `iteration.pack.decision` (e.g. `1.2.3`) is accepted everywhere instead of ids.
- Every state change needs `--why`: a real reason from the conversation. Regressions are allowed with a reason.

## Commands
```
init --lang xx | config [key value] | iter-new T | pack-new T [--iter I] | pack-rm P --why W
add T --pack P --question Q [--doc f] [--chosen X --alternatives X --reason X] --why W
detail ID [--question|--chosen|--alternatives|--reason X] --why W | set ID todo|doing|done|validated --why W [fields]
move ID P --why W | merge KEEP ABSORB --why W [--title T] | review [P]
next [--all] | status | show ID | log -n N | verify | seal --why W [--rebase] | export | scan | import PLAN [--dry-run]
```

## Precision (the script refuses otherwise)
Each decision has 4 fields: `question` (required at creation), `chosen` + `reason` (required for done), `alternatives` (required for validated; `none` only if truly none). ≥10 characters, concrete: names, versions, values, criteria.
- Title = precise subject; question = specific and interrogative. One sentence mixing several topics = several decisions.
- Fill fields only from what the user said or what the sources state. Information missing → ask ONE grouped question, or leave the decision at the lower state. Never invent a reason or generic filler.
- A Validated decision is edited only after setting it back to done/doing (with a reason), then `detail`. Validate only when the user asks.

## Workflows
- **"What next / where are we"**: run `D next`, show the table verbatim (every row), at most one line before it, then a short recommendation citing indexes. If `⚠` appears, say so first and say what to ask the user. Do not re-read `next.md`.
- **No registry**: if the project has history (docs, git, chats), offer adoption and read `${CLAUDE_SKILL_DIR}/references/adopt.md`; otherwise `D init --lang <user's language>`, then check the detected `doc_dir` fits the project's conventions (`D config doc_dir …` if not).
- **Full or near-full pack** (`add` warns or overflows): look at the merge candidates, judge semantic duplicates too, present a table (keep | absorb | why | risk), merge only after explicit consent. Tell the user when a decision went to an overflow pack; propose a thematic split (`pack-new` + `move`) if the "(2)" pack deserves a real name.
- **Integrity**: `⚠ journal` in `status`/`next` → run `D verify` and report faithfully. Never `seal --rebase` without explicit consent. Details: `${CLAUDE_SKILL_DIR}/references/integrity.md`.
- Be economical: when the user gives the details with a state change, ONE `set ID done --chosen … --reason … --alternatives … --why …` (no prior `show`/`detail`). Answer in one line after write commands (index, change); do not paste script output.
- Human-facing command reference: `${CLAUDE_SKILL_DIR}/decisions.md`; read it only when the user asks for help with commands.
