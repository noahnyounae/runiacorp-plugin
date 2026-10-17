---
description: "One decision, pack or iteration with its full history"
argument-hint: "<index|id>  e.g. 1.2.3"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py show $ARGUMENTS 2>&1 || true`

Summarize in a few lines: state, document, dated history with reasons. Reply in the user's language.
