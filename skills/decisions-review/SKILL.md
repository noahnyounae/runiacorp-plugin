---
description: "Find mergeable decisions in full or near-full packs"
argument-hint: "[pack] [--all]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py *)
---
!`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py review $ARGUMENTS 2>&1 || true`

The candidates come from a heuristic (same document, similar titles) that misses semantic duplicates. For each pack shown: reread the decision titles (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/decisions/scripts/dec.py next`) and, only if needed, document excerpts; judge merges including pairs the heuristic missed; present a table (keep | absorb | why merge | risk: lowest state is kept) and ask for consent. Merge NOTHING before explicit consent. Reply in the user's language.
