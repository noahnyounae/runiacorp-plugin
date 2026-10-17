---
description: "Write every open question to a Markdown file, to answer them one by one"
argument-hint: "[--all] [--out file] [--force]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py questions $ARGUMENTS 2>&1 || true`

Tell the user where the file is and how it works: under each question, fill the answer lines (chosen option + reason to finish a decision; alternatives and State = validated to validate), then run `/runiacorp-plugin:decisions-answers`. Offer to go through the questions one by one here instead (ask each in turn, then save with `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py set …`). If it refused because of unapplied answers, offer `/runiacorp-plugin:decisions-answers` first. Reply in the user's language.
