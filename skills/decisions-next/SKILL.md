---
description: "Table of decisions with state and next step (what should I do next?)"
argument-hint: "[--all] [--width N]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py next $ARGUMENTS 2>&1 || true`

Show the table above verbatim, every row (Validated ones included), never as a list. At most one line before it; then recommend which decision(s) to handle first, citing indexes. If ⚠ appears, say so first. For each cell showing a missing-field marker, say in one sentence what to ask the user. The full untruncated table is in `.decisions/next.md`. Reply in the user's language.
