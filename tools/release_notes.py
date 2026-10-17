#!/usr/bin/env python3
"""Print the CHANGELOG section for a release tag (vX.Y.Z).

Exits 1 when the tag, .claude-plugin/plugin.json, the VERSION in dec.py and the CHANGELOG disagree,
so a mis-tagged release never gets published. Usage: python3 tools/release_notes.py v1.0.0
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(tag):
    v = tag.removeprefix("v")
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    m = re.search(r'^VERSION = "([^"]+)"', (ROOT / "skills" / "decisions" / "scripts" / "dec.py").read_text(encoding="utf-8"), re.M)
    script = m.group(1) if m else None
    errors = [f"{what} is {got!r}, tag is {v!r}" for what, got in (("plugin.json version", plugin), ("dec.py VERSION", script)) if got != v]
    sec = re.search(rf"^## \[{re.escape(v)}\][^\n]*\n(.*?)(?=^## \[|\Z)", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.S | re.M)
    if not sec:
        errors.append(f"CHANGELOG.md has no '## [{v}]' section")
    if errors:
        print("\n".join(f"error: {e}" for e in errors), file=sys.stderr)
        sys.exit(1)
    print(sec.group(1).strip())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: release_notes.py vX.Y.Z")
    main(sys.argv[1])
