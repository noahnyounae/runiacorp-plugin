---
description: "Inventory an existing project (docs, git, chats) before adopting it"
argument-hint: "[--max N] [--session ID --grep regex --context]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py scan $ARGUMENTS 2>&1 || true`

If this is a project inventory (not a session detail), continue with the adoption workflow: read `${CLAUDE_PLUGIN_ROOT}/skills/decisions/references/adopt.md`, analyze the inventory above, dig only where useful, turn each candidate into ONE precise question (use the `↳ in reply to` line), propose a plan, and ask your doubts in one grouped question. Import nothing without consent. Reply in the user's language.
