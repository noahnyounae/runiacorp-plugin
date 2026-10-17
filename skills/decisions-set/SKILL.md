---
description: "Change a decision's state (todo|doing|done|validated), with a reason"
argument-hint: "<index> <state> --why \"…\" [--chosen …] [--reason …] [--alternatives …]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py set $ARGUMENTS 2>&1 || true`

done requires chosen + reason; validated also requires alternatives. If the script refuses for insufficient detail, supply the fields from the conversation or ask. Validate ONLY if the user explicitly asks. Also report induced pack/iteration changes. The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; ask ONE grouped question if needed) and rerun with the Bash tool: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py set …`. Otherwise confirm in ONE line. Reply in the user's language.
