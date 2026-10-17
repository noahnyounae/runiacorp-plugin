---
description: "Show or set project config (lang, max_pack, min_field, doc_dir)"
argument-hint: "[key value]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py config $ARGUMENTS 2>&1 || true`

Confirm in one line. If the output asks for a translation (no catalog for the language), translate `${CLAUDE_PLUGIN_ROOT}/skills/decisions/i18n/en.json` into the file it names (same keys and placeholders). Reply in the user's language.
