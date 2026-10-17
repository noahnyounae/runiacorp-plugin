---
description: "Open a new iteration (the previous one must be Validated)"
argument-hint: "\"title\" [--why \"…\"]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py iter-new $ARGUMENTS 2>&1 || true`

The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; ask ONE grouped question if needed) and rerun with the Bash tool: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py iter-new …`. Otherwise confirm in ONE line. Reply in the user's language.
