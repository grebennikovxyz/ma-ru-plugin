"""Build a single installable plugin package, restricted to distributable files."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "ma-ru"
FILES = (
    "plugin.json",
    ".codex-plugin/plugin.json",
    "mcp.json",
    ".claude-plugin/plugin.json",
    ".mcp.json",
    "skills/ma-ru/SKILL.md",
    "assets/envelope.svg",
)
version = json.loads((PLUGIN / "plugin.json").read_bytes())["version"]
archive = ROOT / "dist" / f"ma-ru-{version}.zip"
archive.parent.mkdir(exist_ok=True)
with ZipFile(archive, "w", ZIP_DEFLATED) as output:
    for name in FILES:
        output.write(PLUGIN / name, name)
    for name in ("LICENSE", "NOTICE", "README.md"):
        output.write(ROOT / name, name)
with ZipFile(archive) as output:
    assert output.testzip() is None
    for name in FILES:
        if name.endswith(".json"):
            json.loads(output.read(name))
print(archive)
