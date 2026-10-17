# decisions — command reference

A registry of project decisions: **decision → pack → iteration**, ordered states, a justified journal chained by hash, precise 4-field decisions. Part of the `runiacorp-plugin` plugin.

Claude writes everything you read (titles, questions, documents, tables) **in your language**. Script messages follow the project language (`en`, `fr` shipped; any other language via a translated catalog, see [Languages](#languages)).

## Using it

- **Natural language**: "we choose PostgreSQL for the database", "what should I do next?". The `decisions` skill picks it up and runs the commands.
- **Slash commands** (plugin-namespaced): `/runiacorp-plugin:decisions-next`, `/runiacorp-plugin:decisions-set 1.1.1 done --why "…"`, … One per command, listed below. Read commands run before Claude answers (no tool round-trip); they cost no context until you use them.
- **Direct CLI**: `python3 <plugin>/skills/decisions/scripts/dec.py <command>`; `-h` on any command prints its options; `--version` prints plugin and format versions.

## Model

| Level | Role | State |
|---|---|---|
| **Decision** | settles one question; linked to a document | set by you: `todo < doing < done < validated` |
| **Pack** | related decisions (same subject or period); max `max_pack` (default 6) | computed = lowest of its decisions |
| **Iteration** | a cycle of packs | computed = lowest of its packs |

- A new iteration opens only when the previous one is **Validated**; one active iteration at a time.
- A full pack sends new decisions to an **overflow pack** on the same subject ("Stack (2)", "Stack (3)"…). Before that, merge candidates are shown.
- An empty pack counts as `todo` (it blocks its iteration until filled or deleted with `pack-rm`).
- Every state change is journaled with its justification; derived pack/iteration changes are journaled automatically (`auto`).
- **Index** `iteration.pack.decision`: `1` = iteration 1, `1.2` = pack 2, `1.2.3` = decision 3 of that pack. Never reused; a moved decision gets a new index. Commands accept the index or the internal id (`C3`, `P2`, `I1`).
- **States** are accepted in any shipped language, case/accents insensitive: `todo|doing|done|validated` (aliases `wip`, `ok`).

### The 4 fields
| Field | Content | Required |
|---|---|---|
| `question` | the precise question settled | at creation (`--question`) |
| `chosen` | the chosen option, named precisely | to reach **done** |
| `reason` | why (criterion, fact) | to reach **done** |
| `alternatives` | rejected options with their motive (or `none`) | to reach **validated** |

At least `min_field` characters (default 10), concrete. They are journaled (chain-protected), replay-checked by `verify`, shown by `next`, and written into the decision's document inside a block between `<!-- decisions:C1 -->` markers; text outside the markers is never touched, and several decisions can share a document. A Validated decision is edited only after setting it back to done/doing.

## Commands

Slash name = `/runiacorp-plugin:decisions-<command>`.

| Command | Purpose |
|---|---|
| `init [--lang xx] [--doc-dir d] [--max-pack N]` | create `.decisions/` (project language, document folder auto-detected: `docs/decisions`, `doc/decisions`…) |
| `config [key value] [--why …]` | show/set `lang`, `max_pack`, `min_field`, `doc_dir` (changes are journaled) |
| `iter-new "title" [--why] [--force]` | open an iteration (previous must be Validated) |
| `pack-new "title" [--iter N] [--kind link\|time]` | create a pack |
| `pack-rm PACK --why …` | delete an empty pack |
| `add "title" --pack P --question Q [--doc f] [--chosen --alternatives --reason] [--why] [--no-overflow] [--force]` | add a decision; document created, or its block appended; default document `<doc_dir>/<slug>.md` |
| `detail ID [--question --chosen --alternatives --reason] --why …` | set/correct the 4 fields (refused on Validated) |
| `set ID STATE --why … [fields] [--force]` | change state; done/validated require the fields (can be passed in the same call); validating records the document hash; regression allowed with a reason (`--force` if a later iteration started) |
| `move ID PACK --why … [--force]` | move to another pack (refused into a full pack) |
| `merge KEEP ABSORB --why … [--title T]` | merge two decisions of one pack: lowest state kept, missing fields inherited, absorbed document kept and referenced |
| `review [PACK] [--all]` | merge candidates (same document, similar titles) in full or near-full packs |
| `next [--all] [--width N]` | one Markdown table per pack: index, decision, question, chosen, alternatives, reason, state, next step (names missing fields). Also writes the **full** table to `.decisions/next.md` |
| `status [--all]` | tree view |
| `show ID` | record + full history |
| `log [-n N] [--hash]` | recent journal events |
| `export [--out f]` | readable recap in `.decisions/export.md` |
| `verify [--head]` | integrity check (exit 2 if altered/unsealed) |
| `seal --why … [--rebase]` | chain a legacy journal / rebuild the chain after an accepted alteration |
| `scan [--max N] [--session ID --grep re --context]` | inventory of an existing project |
| `import PLAN [--dry-run] [--append]` | import a retroactive plan |

## Integrity (transparency)

Each journal entry holds `prev` and `h` (sha256 of its content). `index.json` stores the head. `verify` detects an edited, deleted, inserted or reordered entry, a truncated tail, and an index that disagrees with a replay of the journal; it warns when a document changed after its validation. Writing commands refuse to run on an altered journal. `seal --rebase` accepts a known alteration and records it. For a strong guarantee, anchor `verify --head` outside the folder (git commit, ticket). `config.json` and `next.md` are outside the chain (config changes are journaled).

## Adopting an existing project

`scan` → plan (JSON) → `import --dry-run` → `import`. Each chat excerpt comes with the assistant remark it answers, and multiple-choice answers are included. Plan format and rules: `references/adopt.md`. Imports enforce the same precision rules: `question` required; `chosen`+`reason` for done/validated; `alternatives` too for validated; packs split automatically beyond `max_pack`.

## Languages

`init --lang xx` (or `config lang xx`) sets the project language. Catalogs: `i18n/en.json`, `i18n/fr.json`. For another language, ask Claude: it translates `i18n/en.json` into `.decisions/i18n/<code>.json` (project-local, shareable through git) keeping keys and placeholders; the script merges it over English. Until then English is used and Claude relays in your language.

## Files

```
<project>/.decisions/
  config.json   lang, max_pack, min_field, doc_dir (commit it)
  index.json    structure and states (never edit)
  log.jsonl     chained journal (append-only)
  next.md       last `next` table, untruncated (generated)
  export.md     recap (generated)
  i18n/         optional project-local language catalogs
  log.jsonl.before-seal-*   backups made by seal
```

## Common errors

| Message | Fix |
|---|---|
| journal altered, writes blocked | `verify`; if known and accepted, `seal --rebase --why …` |
| journal not sealed | legacy journal: `seal --why migration` |
| Not enough detail to move to Done/Validated | pass `--chosen --reason` (done), plus `--alternatives` (validated) |
| … too vague | field shorter than `min_field`: be concrete |
| Iteration N is not Validated | validate its decisions, or `--force` (justified) |
| Registry format … newer/older | update the plugin / unsupported old format |
| Document outside the project | use a relative path inside the project |
