---
description: "Make a decision obsolete by replacing it with another decision"
argument-hint: "<old> <new> --why \"…\""
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py obsolete $ARGUMENTS 2>&1 || true`

Use it when a newer decision overrides an older one; ask which decision replaces which if unclear. The old decision keeps its history and document (marked as superseded) and stops counting in pack/iteration states and limits; restore it with `/runiacorp-plugin:decisions-set <old> doing --why …`. Never make a decision obsolete unless the user says so. The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; ask ONE grouped question if needed) and rerun with the Bash tool: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py obsolete …`. Otherwise confirm in ONE line. Reply in the user's language.
