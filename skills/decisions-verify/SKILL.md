---
description: "Check the integrity of the hash-chained journal"
argument-hint: "[--head]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py verify $ARGUMENTS 2>&1 || true`

Report the result faithfully (OK / ALTERED with the lines / UNSEALED, and ⚠ warnings). Minimize nothing; fix nothing without consent. If UNSEALED, propose `/runiacorp-plugin:decisions-seal`. Reply in the user's language.
