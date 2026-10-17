---
description: "Import a retroactive plan (JSON) into the registry"
argument-hint: "<plan.json> [--dry-run] [--append]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
Always run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py import $ARGUMENTS --dry-run` first, show the resulting tree, get the user's explicit OK, then run it without `--dry-run`, then `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py verify`. If there is no plan yet, follow `${CLAUDE_PLUGIN_ROOT}/skills/decisions/references/adopt.md` (start with `/runiacorp-plugin:decisions-scan`). Reply in the user's language.
