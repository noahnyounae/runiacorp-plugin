---
description: "Read the filled questions document and apply the answers"
argument-hint: "[--file path] [--dry-run]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py answers $ARGUMENTS 2>&1 || true`

Summarize in a few lines: what was applied, what was saved as detail only, what was skipped, and each error with what is missing. Preview with `--dry-run` only if the user asks. Never fill in missing answers yourself. Reply in the user's language.
