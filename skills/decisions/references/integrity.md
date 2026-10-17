# Journal integrity

`.decisions/log.jsonl` is hash-chained: every entry holds `prev` (previous entry's hash) and `h` (sha256 of its content). `index.json` stores the head hash. Every writing command refuses to run on an altered or unsealed journal.

`D verify` (exit 0 = ok, 2 = altered/unsealed):
| Check | Detects |
|---|---|
| per-entry hash | an entry edited (line number given) |
| `prev` chaining | an entry deleted, inserted or moved |
| head = index head | journal tail truncated; index edited; write interrupted |
| journal replay vs index | states, packs, documents or the 4 fields falsified in the index |
| ⚠ warnings (not errors) | a document edited after its validation; clock going backwards; a pack above the limit; Done/Validated decisions with incomplete detail |

Handling:
- **ALTERED**: report the lines and problems exactly; do not minimize or fix silently. Ask the user whether the alteration is known. Only with explicit consent: `D seal --rebase --why "<reason>"` (rebuilds the chain, backs up the old journal, records the alteration and the previous head in the journal).
- **UNSEALED** (legacy journal without hashes): `D seal --why "migration"`.
- **Document modified since validation** (⚠): tell the user; offer to set the decision back to `doing` (justified regression) or to accept the edit.
- Limits: the chain detects after-the-fact edits but cannot stop someone who rewrites everything and recomputes all hashes. For a strong guarantee, suggest anchoring `D verify --head` outside the folder (git commit, ticket): a diverging head proves a rewrite. `config.json` and `next.md` are not covered by the chain (config changes are journaled).
