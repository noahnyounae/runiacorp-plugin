---
description: "Initialize the decision registry in the current project"
argument-hint: "[--lang code] [--doc-dir path] [--max-pack N]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
Detect the user's language (ISO code) and run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py init --lang <code> $ARGUMENTS` with Bash (omit --lang only if `$ARGUMENTS` already has it). Then state the detected `doc_dir` and offer to adjust it (`config`) to the project's conventions. If the project has docs, git history or past chats, offer `/runiacorp-plugin:decisions-scan`. If the script reports a missing catalog, translate it as `/runiacorp-plugin:decisions-config` describes. Reply in the user's language.
