---
description: "Recent journal events"
argument-hint: "[-n N] [--hash]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py log $ARGUMENTS 2>&1 || true`

Show as a Markdown table (date | type | element | change | reason). Reply in the user's language.
