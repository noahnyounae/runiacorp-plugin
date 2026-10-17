---
description: "Merge two decisions of one pack (the first is kept, the second absorbed)"
argument-hint: "<keep> <absorb> --why \"…\" [--title \"…\"]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py merge $ARGUMENTS 2>&1 || true`

The kept decision takes the lowest state and inherits missing fields; the absorbed document is kept and referenced. The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; ask ONE grouped question if needed) and rerun with the Bash tool: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py merge …`. Otherwise confirm in ONE line. Reply in the user's language.
