---
description: "Seal or migrate the journal, or rebuild the chain after an accepted alteration"
argument-hint: "--why \"…\" [--rebase]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
First run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py verify` and show the result. NEVER use `--rebase` without the user's explicit consent in this conversation (it rebuilds the chain; the alteration stays recorded in the journal). Then run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py seal $ARGUMENTS`. A `--why` is required: ask for it if missing. Reply in the user's language.
