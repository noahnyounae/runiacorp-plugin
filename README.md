# runiacorp-plugin

Runiacorp skills for [Claude Code](https://code.claude.com), shipped as one plugin and one marketplace (`runiacorp`) from this repository.

| Skill | What it does |
|---|---|
| [`decisions`](skills/decisions/decisions.md) | Archive, classify and audit the decisions of a mid/long-term project: decision → pack → iteration, 4 states, precise 4-field decisions, hash-chained journal, adoption of existing projects. Works in the user's language. |

More skills will be added under `skills/`; they all ship through this same plugin.

## Install

In Claude Code (or the same commands prefixed with `claude plugin …` in a shell):

```
/plugin marketplace add noahnyounae/runiacorp-plugin
/plugin install runiacorp-plugin@runiacorp
```

The repository can be private: Claude Code uses the git credentials already on the machine (`gh auth login && gh auth setup-git`, or an SSH key loaded in `ssh-agent`). Without a GitHub SSH key set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`.

Share it with a whole repository's contributors: `claude plugin marketplace add noahnyounae/runiacorp-plugin --scope project`, then commit the `.claude/settings.json` it writes.

If you previously copied the `decisions` skill or its `decisions-*` commands into `~/.claude/skills` or `~/.claude/commands`, remove them: the plugin replaces them and duplicates confuse the model.

## Updates (several machines)

- **Release**: bump `version` in `.claude-plugin/plugin.json` (installed copies only update when it changes), add a `CHANGELOG.md` entry, push.
- **Each machine**: turn on **Enable auto-update** for the `runiacorp` marketplace (`/plugin` → Marketplaces), or update by hand: `/plugin marketplace update runiacorp` or `claude plugin update runiacorp-plugin@runiacorp`. For a managed fleet, set `autoUpdate` on the marketplace in managed settings.
- **Continuous delivery instead**: remove `version` from `plugin.json`; every pushed commit then counts as an update (less control, no release gate).
- **Private repo + auto-update**: needs a credential the git helper can supply without prompting; add `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE=1` to keep the last working copy if the background check cannot authenticate.
- Registry data (`.decisions/`) travels with each project's own git. Its `index.json` carries a format number: an older plugin refuses a newer registry with an explicit "update the plugin" message.

## Using the decisions skill

Say what you decided ("we choose PostgreSQL 16 for the database because …") or ask "what should I do next?". Or use the slash commands, all namespaced by the plugin:

`/runiacorp-plugin:decisions-next`, `-status`, `-add`, `-set`, `-detail`, `-move`, `-merge`, `-review`, `-pack-new`, `-pack-rm`, `-iter-new`, `-show`, `-log`, `-verify`, `-seal`, `-export`, `-scan`, `-import`, `-config`, `-init`.

Full reference: [skills/decisions/decisions.md](skills/decisions/decisions.md). To avoid permission prompts on a trusted machine, allow `Skill(runiacorp-plugin:decisions)` and `Bash(python3 */skills/decisions/scripts/dec.py *)` in your Claude Code permissions.

## Repository layout

```
.claude-plugin/
  plugin.json            plugin manifest (name, version)
  marketplace.json       marketplace "runiacorp" listing this plugin (source "./")
skills/
  decisions/             the skill (SKILL.md, scripts/, i18n/, references/, decisions.md)
  decisions-<cmd>/       GENERATED slash commands (do not edit by hand)
tools/build_skills.py    generates the slash commands from one spec
tests/                   unit tests (python3 -m unittest discover -s tests)
CHANGELOG.md
```

## Conventions for every skill in this plugin

- **English source, user-language output.** Skills, scripts and references are written in English. They instruct Claude to reply, and to write every document, text or table the user will read, in the user's language. Script messages come from `i18n/<lang>.json` catalogs (English fallback, project-local catalogs for other languages).
- **Spend tokens only when needed.** Keep each `SKILL.md` short (the test enforces < 900 words for `decisions`); put rare workflows in `references/` loaded on demand; do deterministic work in scripts and print compact output. Slash-only helpers use `disable-model-invocation: true` so their descriptions never enter the context.
- **Portable paths.** Use `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}`, never absolute machine paths (a test enforces it).
- **Descriptions** start with what the skill does and when to use it; the key trigger first (listing truncates at 1,536 characters).

### Adding a skill

1. Create `skills/<name>/SKILL.md` (+ `scripts/`, `references/`, `i18n/` as needed). Add slash helpers the same way `tools/build_skills.py` does, or by hand with `disable-model-invocation: true`.
2. Add tests under `tests/`, a `CHANGELOG.md` entry, bump `version`, update the table above.
3. `python3 -m unittest discover -s tests && claude plugin validate .`

## Develop and test

```
python3 tools/build_skills.py              # regenerate slash commands after editing the spec
python3 -m unittest discover -s tests -v   # 23 tests: lifecycle, packs, tampering, languages, import/scan, packaging
claude plugin validate .                   # manifests
claude --plugin-dir .                      # try the plugin in a session without installing; /reload-plugins after edits
```

Non-interactive (`claude -p`) runs deny the Skill tool unless pre-approved: add `--allowedTools "Skill(runiacorp-plugin:decisions)" "Bash(python3 …/dec.py *)"`.

### Release checklist

- [ ] tests and `claude plugin validate .` pass
- [ ] `version` bumped in `plugin.json` and `VERSION` in `skills/decisions/scripts/dec.py` (the test checks they match the changelog)
- [ ] `CHANGELOG.md` updated
- [ ] if the registry data format changed: bump `FORMAT` in `dec.py`, document the migration
- [ ] commit, tag `v<version>`, push
