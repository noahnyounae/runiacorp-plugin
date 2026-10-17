---
description: "Set or correct the 4 fields of a decision (question, chosen, alternatives, reason)"
argument-hint: "<index> [--question …] [--chosen …] [--reason …] [--alternatives …] --why \"…\""
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py detail $ARGUMENTS 2>&1 || true`

Refused on a Validated decision: set it back with `/runiacorp-plugin:decisions-set` first. The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; ask ONE grouped question if needed) and rerun with the Bash tool: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py detail …`. Otherwise confirm in ONE line. Reply in the user's language.
