---
description: "Write a readable recap to .decisions/export.md"
argument-hint: "[--out file.md]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py export $ARGUMENTS 2>&1 || true`

Give the generated path in one line; do not open the file. Reply in the user's language.
