"""Check distribution metadata, or synchronize it with the Python package version."""

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/ma-ru"
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"][
    "version"
]


def synchronize(write=False):
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", VERSION):
        raise SystemExit("Use a stable major.minor.patch release.")
    stale = []

    def update(path, transform):
        original = path.read_text("utf-8")
        expected = transform(original)
        if original != expected:
            stale.append(path.relative_to(ROOT))
            if write:
                path.write_text(expected, "utf-8", newline="\n")

    def manifest(text):
        data = json.loads(text)
        data["version"] = VERSION
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    for relative in (
        "plugin.json",
        ".codex-plugin/plugin.json",
        ".claude-plugin/plugin.json",
    ):
        update(PLUGIN / relative, manifest)
    update(ROOT / "n8n/package.json", manifest)

    def lock(text):
        data = json.loads(text)
        data["version"] = data["packages"][""]["version"] = VERSION
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    update(ROOT / "n8n/package-lock.json", lock)
    update(
        ROOT / "n8n/nodes/MaRu/MaRu.node.ts",
        lambda s: re.sub(
            r"(name: 'n8n-nodes-ma-ru', version: ')[^']+(')", rf"\g<1>{VERSION}\2", s
        ),
    )
    for path in (ROOT / "README.md", ROOT / "n8n/README.md"):
        update(
            path,
            lambda s: re.sub(
                r"(?<=ma-ru-)\d+\.\d+\.\d+(?=-clawhub\.tgz|\.tgz)|(?<=releases/download/v)\d+\.\d+\.\d+(?=/n8n-nodes-ma-ru-)",
                VERSION,
                s,
            ),
        )

    for relative, source in (
        (".claude-plugin/marketplace.json", "./plugins/ma-ru"),
        (
            ".agents/plugins/marketplace.json",
            {"source": "local", "path": "./plugins/ma-ru"},
        ),
    ):
        catalog = json.loads((ROOT / relative).read_bytes())
        entries = [item for item in catalog["plugins"] if item["name"] == "ma-ru"]
        if (
            len(entries) != 1
            or entries[0]["source"] != source
            or catalog["name"] != "grebennikov-ma-ru"
        ):
            raise SystemExit(f"Invalid Ma-Ru installation source in {relative}")
        if "version" in entries[0] and entries[0]["version"] != VERSION:
            raise SystemExit(f"Stale marketplace override in {relative}")
    if stale and not write:
        raise SystemExit(
            "Run python scripts/marketplace_versions.py --sync: "
            + ", ".join(map(str, stale))
        )
    print(f"Claude Code, Codex, OpenClaw bundle and n8n use Ma-Ru {VERSION}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true")
    synchronize(parser.parse_args().sync)
