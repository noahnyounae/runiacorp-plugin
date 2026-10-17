#!/usr/bin/env python3
"""Generate the slash-command skills (skills/decisions-<cmd>/SKILL.md) from one spec.

Each is `disable-model-invocation: true`: zero permanent context cost, only run when the user types the command.
Usage: python3 tools/build_skills.py [--check]   (--check fails if generated files are out of date)
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = "runiacorp-plugin"
DEC = "${CLAUDE_PLUGIN_ROOT}/skills/decisions"
RUN = f"python3 {DEC}/scripts/dec.py"
LANG = "Reply in the user's language."
WRITE = (f"The command already ran above: do NOT run it again unless the output is an ERROR. If the output above is an ERROR about a missing or invalid argument, complete it from the conversation (never invent a reason or any of the 4 fields; "
         f"ask ONE grouped question if needed) and rerun with the Bash tool: `{RUN} <cmd> …`. Otherwise confirm in ONE line. {LANG}")

# (name, description, argument-hint, mode, note)  mode: inject = run before Claude answers; run = Claude runs it (guarded)
SPEC = [
    ("next", "Table of decisions with state and next step (what should I do next?)", "[--all] [--width N]", "inject",
     f"Show the table above verbatim, every row (Validated ones included), never as a list. At most one line before it; then recommend which decision(s) to handle first, citing indexes. "
     f"If ⚠ appears, say so first. For each cell showing a missing-field marker, say in one sentence what to ask the user. The full untruncated table is in `.decisions/next.md`. {LANG}"),
    ("status", "Tree view of the active iteration (packs and unvalidated decisions)", "[--all]", "inject", f"Show the output as is. If it starts with ⚠, say so first. {LANG}"),
    ("show", "One decision, pack or iteration with its full history", "<index|id>  e.g. 1.2.3", "inject", f"Summarize in a few lines: state, document, dated history with reasons. {LANG}"),
    ("log", "Recent journal events", "[-n N] [--hash]", "inject", f"Show as a Markdown table (date | type | element | change | reason). {LANG}"),
    ("verify", "Check the integrity of the hash-chained journal", "[--head]", "inject",
     f"Report the result faithfully (OK / ALTERED with the lines / UNSEALED, and ⚠ warnings). Minimize nothing; fix nothing without consent. If UNSEALED, propose `/{PLUGIN}:decisions-seal`. {LANG}"),
    ("export", "Write a readable recap to .decisions/export.md", "[--out file.md]", "inject", f"Give the generated path in one line; do not open the file. {LANG}"),
    ("review", "Find mergeable decisions in full or near-full packs", "[pack] [--all]", "inject",
     f"The candidates come from a heuristic (same document, similar titles) that misses semantic duplicates. For each pack shown: reread the decision titles (`{RUN} next`) and, only if needed, document excerpts; "
     f"judge merges including pairs the heuristic missed; present a table (keep | absorb | why merge | risk: lowest state is kept) and ask for consent. Merge NOTHING before explicit consent. {LANG}"),
    ("scan", "Inventory an existing project (docs, git, chats) before adopting it", "[--max N] [--session ID --grep regex --context]", "inject",
     f"If this is a project inventory (not a session detail), continue with the adoption workflow: read `{DEC}/references/adopt.md`, analyze the inventory above, dig only where useful, "
     f"turn each candidate into ONE precise question (use the `↳ in reply to` line), propose a plan, and ask your doubts in one grouped question. Import nothing without consent. {LANG}"),
    ("config", "Show or set project config (lang, max_pack, min_field, doc_dir)", "[key value]", "inject",
     f"Confirm in one line. If the output asks for a translation (no catalog for the language), translate `{DEC}/i18n/en.json` into the file it names (same keys and placeholders). {LANG}"),
    ("iter-new", "Open a new iteration (the previous one must be Validated)", "\"title\" [--why \"…\"]", "inject", WRITE.replace("<cmd>", "iter-new")),
    ("pack-new", "Create a pack of related decisions in the active iteration", "\"title\" [--iter N] [--kind link|time] [--why \"…\"]", "inject", WRITE.replace("<cmd>", "pack-new")),
    ("pack-rm", "Delete an empty pack", "<pack> --why \"…\"", "inject", WRITE.replace("<cmd>", "pack-rm")),
    ("add", "Add a precise decision (question required; document created or completed)", "\"title\" --pack 1.1 --question \"…\" [--doc path] [--chosen …] [--reason …] [--alternatives …] [--why …]", "inject",
     f"One decision = ONE question: precise title, specific interrogative `--question`; pass `--chosen/--reason/--alternatives` only if the user already gave them; split mixed topics into several adds. "
     f"If the output mentions an overflow pack or merge candidates, tell the user and offer `/{PLUGIN}:decisions-review`. " + WRITE.replace("<cmd>", "add")),
    ("detail", "Set or correct the 4 fields of a decision (question, chosen, alternatives, reason)", "<index> [--question …] [--chosen …] [--reason …] [--alternatives …] --why \"…\"", "inject",
     "Refused on a Validated decision: set it back with `/" + PLUGIN + ":decisions-set` first. " + WRITE.replace("<cmd>", "detail")),
    ("set", "Change a decision's state (todo|doing|done|validated), with a reason", "<index> <state> --why \"…\" [--chosen …] [--reason …] [--alternatives …]", "inject",
     "done requires chosen + reason; validated also requires alternatives. If the script refuses for insufficient detail, supply the fields from the conversation or ask. "
     "Validate ONLY if the user explicitly asks. Also report induced pack/iteration changes. " + WRITE.replace("<cmd>", "set")),
    ("move", "Move a decision to another pack", "<index> <pack> --why \"…\"", "inject", WRITE.replace("<cmd>", "move")),
    ("merge", "Merge two decisions of one pack (the first is kept, the second absorbed)", "<keep> <absorb> --why \"…\" [--title \"…\"]", "inject",
     "The kept decision takes the lowest state and inherits missing fields; the absorbed document is kept and referenced. " + WRITE.replace("<cmd>", "merge")),
    ("questions", "Write every open question to a Markdown file, to answer them one by one", "[--all] [--out file] [--force]", "inject",
     f"Tell the user where the file is and how it works: under each question, fill the answer lines (chosen option + reason to finish a decision; alternatives and State = validated to validate), then run `/{PLUGIN}:decisions-answers`. "
     f"Offer to go through the questions one by one here instead (ask each in turn, then save with `{RUN} set …`). If it refused because of unapplied answers, offer `/{PLUGIN}:decisions-answers` first. {LANG}"),
    ("answers", "Read the filled questions document and apply the answers", "[--file path] [--dry-run]", "inject",
     f"Summarize in a few lines: what was applied, what was saved as detail only, what was skipped, and each error with what is missing. Preview with `--dry-run` only if the user asks. Never fill in missing answers yourself. {LANG}"),
    ("conflicts", "Check decisions for contradictions or conflicts and open resolving decisions", "[--create] [--pack] [--dismiss A B --why …]", "inject-digest",
     "{{file:references/conflicts.md}}\n\n" + LANG),
    ("init", "Initialize the decision registry in the current project", "[--lang code] [--doc-dir path] [--max-pack N]", "run",
     f"Detect the user's language (ISO code) and run `{RUN} init --lang <code> $ARGUMENTS` with Bash (omit --lang only if `$ARGUMENTS` already has it). "
     f"Then state the detected `doc_dir` and offer to adjust it (`config`) to the project's conventions. If the project has docs, git history or past chats, offer `/{PLUGIN}:decisions-scan`. "
     f"If the script reports a missing catalog, translate it as `/{PLUGIN}:decisions-config` describes. {LANG}"),
    ("seal", "Seal or migrate the journal, or rebuild the chain after an accepted alteration", "--why \"…\" [--rebase]", "run",
     f"First run `{RUN} verify` and show the result. NEVER use `--rebase` without the user's explicit consent in this conversation (it rebuilds the chain; the alteration stays recorded in the journal). "
     f"Then run `{RUN} seal $ARGUMENTS`. A `--why` is required: ask for it if missing. {LANG}"),
    ("import", "Import a retroactive plan (JSON) into the registry", "<plan.json> [--dry-run] [--append]", "run",
     f"Always run `{RUN} import $ARGUMENTS --dry-run` first, show the resulting tree, get the user's explicit OK, then run it without `--dry-run`, then `{RUN} verify`. "
     f"If there is no plan yet, follow `{DEC}/references/adopt.md` (start with `/{PLUGIN}:decisions-scan`). {LANG}"),
]


def render(name, desc, hint, mode, note):
    import re
    note = re.sub(r"\{\{file:([^}]+)\}\}", lambda m: (ROOT / "skills" / "decisions" / m.group(1)).read_text(encoding="utf-8").strip(), note)
    note = re.sub(r"\bD (?=[a-z])", f"{RUN} ", note)  # the reference writes the CLI as `D`
    extra = " --digest" if mode == "inject-digest" else ""
    mode = "inject" if mode == "inject-digest" else mode
    fm = ["---", f"description: {json.dumps(desc, ensure_ascii=False)}", f"argument-hint: {json.dumps(hint, ensure_ascii=False)}",
          "disable-model-invocation: true", f"allowed-tools: Bash({RUN} *)", "---", ""]
    body = f"!`{RUN} {name}{extra} $ARGUMENTS 2>&1 || true`\n\n{note}\n" if mode == "inject" else f"{note}\n"
    return "\n".join(fm) + body


def main():
    stale = []
    for spec in SPEC:
        p = ROOT / "skills" / f"decisions-{spec[0]}" / "SKILL.md"
        text = render(*spec)
        if "--check" in sys.argv:
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                stale.append(str(p.relative_to(ROOT)))
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    if stale:
        print("out of date (run tools/build_skills.py):", *stale, sep="\n  ")
        sys.exit(1)
    print(f"{len(SPEC)} command skills {'in sync' if '--check' in sys.argv else 'generated'}")


if __name__ == "__main__":
    main()
