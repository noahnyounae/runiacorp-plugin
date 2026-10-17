# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versioning: the `version` in `.claude-plugin/plugin.json` is the update signal for installed copies; bump it on every release.

## [1.0.0] - 2026-10-17

### Added
- `runiacorp-plugin` plugin with its first skill, **decisions**: decision → pack → iteration registry with 4 states, justified journal, numeric index (`1.2.3`).
- Hash-chained journal with `verify` / `seal`: detects edited, deleted, inserted or reordered entries, truncated tail and falsified index (journal replay); warns when a validated document changes.
- 4-field precise decisions (question, chosen option, rejected alternatives, reason), required progressively, written into the decision's document.
- Packs limited to `max_pack` (default 6) with automatic overflow packs, merge candidates (`review`) and `merge`.
- `next`: one Markdown table per pack, plus the untruncated `.decisions/next.md`.
- Adoption of existing projects: `scan` (documents, git, chats with the question each answer replies to) and `import` (dated, precision-checked).
- Multilingual: skill and scripts in English; replies, documents and script messages in the user's language (`en`, `fr` catalogs; project-local catalogs for any other language).
- Per-project `config.json` (`lang`, `max_pack`, `min_field`, `doc_dir`; document folder auto-detected).
- 20 slash commands (`/runiacorp-plugin:decisions-<command>`), generated from one spec, hidden from the model's context.
- Test suite (Python 3.9+) and GitHub Actions CI/CD: tests on Linux/macOS × Python 3.9/3.12/3.13, strict plugin validation, version-bump reminder, tag-driven GitHub Release (checks tag/version/changelog agree), Dependabot for actions.
