---
description: "Add a precise decision (question required; document created or completed)"
argument-hint: "\"title\" --pack 1.1 --question \"…\" [--doc path] [--chosen …] [--reason …] [--alternatives …] [--why …]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py add $ARGUMENTS 2>&1 || true`

One decision = ONE question: precise title, specific interrogative `--question`; pass `--chosen/--reason/--alternatives` only if the user already gave them; split mixed topics into several adds. If the output mentions an overflow pack or merge candidates, tell the user and offer `/runiacorp-plugin:decisions-review`. The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; ask ONE grouped question if needed) and rerun with the Bash tool: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py add …`. Otherwise confirm in ONE line. Reply in the user's language.
