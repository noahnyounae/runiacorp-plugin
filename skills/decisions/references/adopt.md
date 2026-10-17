# Adopting an existing project

Goal: rebuild a decision registry from what already exists (context files, documents with creation/modification dates, git, chat sessions). Never read every document or chat in full.

1. **Language and registry.** Confirm the user's language, then `D init --lang <code>` (skip if a registry exists; then use `import --append`).
2. **Inventory.** `D scan` (compact): context files, documents with dates, git (commits per month, "decision-like" commits), chat sessions, and decision candidates from chats. Each chat excerpt is followed by `↳ in reply to: …` (the assistant's preceding remark = the question that was settled); answers to multiple-choice questions are tagged `[answer to a question]`.
3. **Dig only where useful.** `D scan --session ID --grep <word> --context` for one session; read a specific document excerpt only when needed. Keyword detection covers en/fr/es/de; for another language, grep with words of the user's language. A document modified long after creation, or a decision contradicted later in a chat, signals a reversal.
4. **Build the plan** (JSON in the scratchpad or a temp dir, never in the project):
```json
{"iterations":[{"title":"..","date":"YYYY-MM-DD","packs":[{"title":"..","kind":"link|time","date":"..","choices":[
 {"title":"precise subject","doc":"optional/path.md","date":"..",
  "question":"the precise question settled","chosen":"option, with name/version","reason":"criterion or fact",
  "alternatives":"rejected options with the reason (or none)","why":"context","src":"chat ID, date / commit / document",
  "history":[{"state":"doing","date":"..","why":".."},{"state":"validated","date":"..","why":".."}]}]}]}]}
```
   - `history` optional (else a single `"state"`). `doc` optional (defaults to `<doc_dir>/<slug>.md`).
   - Iterations = major phases (breaks in dates/activity, milestones). Packs = subjects or periods, at most `max_pack` decisions (the script splits automatically into "(2)", but a thematic split is better). Only the last iteration may be non-Validated.
   - One decision = one question. Split vague or mixed decisions. `question` is mandatory; `chosen` + `reason` are required for done/validated, `alternatives` also for validated, otherwise the import is refused.
   - State heuristic: stable document + decision never revisited → `done`; recent editing → `doing`. **Never `validated` without the user's confirmation** (a human act): propose `done`.
   - Each `why`/`src` cites its source (chat id + date, commit, document). Invent nothing. Doubt → ONE grouped question (iteration boundaries, doubtful states, ambiguous decisions), not one per item. Insufficient source → do not raise the state, ask.
5. **Present** the plan as a short tree (`index title [state]`), get agreement, then `D import plan.json --dry-run`, then `D import plan.json` (dated events are written with their original dates; derived pack/iteration states are logged as "auto: retroactive import"). Then `D verify`.
