---
description: "Check decisions for contradictions or conflicts and open resolving decisions"
argument-hint: "[--create] [--pack] [--dismiss A B --why …]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py conflicts --digest $ARGUMENTS 2>&1 || true`

# Checking decisions for contradictions

`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py conflicts --digest` gives (1) heuristic candidates: a decision rejects what another chose; two decisions answer the same question differently; (2) a compact digest of every closed decision (index | question | chosen | rejected). The heuristic only finds leads; most real contradictions are semantic, so you do the reading.

1. **Judge each candidate** against the digest: a real contradiction, or a legitimate case (e.g. MongoDB rejected for the main database but chosen for an analytics store)?
2. **Scan the digest yourself** for what the heuristic cannot see: incompatible choices (A requires X, B excludes X), mutually exclusive constraints, a later decision silently undoing an earlier one, two decisions imposing different values for the same thing.
3. **Present a table** in the user's language: | Pair | Nature of the conflict | Proposed resolving question |. Say how sure you are for each.
4. **Open resolving decisions for the clear conflicts**: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py conflicts --create` when every new candidate is real; otherwise `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py add "Resolve conflict A / B" --pack <index from python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py conflicts --pack> --question "<specific question>" --refs A,B --why "<where the conflict comes from>"`. A resolving decision is settled later like any other (question → chosen option → reason → alternatives).
5. **False positives**: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py conflicts --dismiss A B --why "<why it is not a conflict>"` (journaled, no longer flagged; `--undismiss A B --why …` restores it). Always tell the user which pairs you dismissed and why, so they can overrule you. Dismiss only when you are confident; otherwise treat it as doubt (next point).
6. **Doubt**: ask the user ONE grouped question instead of creating noise.

Never edit or change the state of the conflicting decisions to "fix" them: the resolution is a new decision that the user settles. If no iteration is active, say a new one is needed (`iter-new`) before conflict decisions can be opened. A conflict decision stays visible in `next` until it is Validated, so conflicts cannot be forgotten.

Reply in the user's language.
