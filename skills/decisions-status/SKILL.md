---
description: "Tree view of the active iteration (packs and unvalidated decisions)"
argument-hint: "[--all]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py status $ARGUMENTS 2>&1 || true`

Show the output as is. If it starts with ⚠, say so first. Reply in the user's language.
