#!/usr/bin/env python3
"""Warn (never fail) when files that reach users changed without a plugin version bump.

Installed copies only update when `version` in .claude-plugin/plugin.json changes.
Usage: python3 tools/check_version_bump.py <base-ref>      (emits a GitHub ::warning:: annotation)
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ.get("REPO_ROOT") or Path(__file__).resolve().parent.parent)
SHIPPED = ("skills/", ".claude-plugin/marketplace.json", "agents/", "hooks/", "commands/")


def shipped(files):
    return [f for f in files if f.startswith(SHIPPED)]


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)


def main(base):
    if not base or set(base) == {"0"}:
        print("no base ref (first push): nothing to compare")
        return
    changed = shipped(git("diff", "--name-only", f"{base}...HEAD").stdout.split())
    old = git("show", f"{base}:.claude-plugin/plugin.json")
    if not changed or old.returncode != 0:
        print("no shipped file changed" if not changed else "base has no plugin.json")
        return
    now = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    if json.loads(old.stdout)["version"] == now:
        print(f"::warning title=Version not bumped::{len(changed)} shipped file(s) changed but plugin version is still {now}; "
              f"installed copies will not update until you bump it in .claude-plugin/plugin.json (and CHANGELOG.md).")
    else:
        print(f"version bumped to {now}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
