"""Build a maintainer handoff for external directories that require human review."""

import json
from urllib.request import Request, urlopen

from marketplace_versions import VERSION

REPO = "https://github.com/grebennikovxyz/ma-ru-plugin"
release = f"{REPO}/releases/tag/v{VERSION}"


def pickaplugin():
    try:
        request = Request(
            "https://pickaplugin.com/catalog.json",
            headers={
                "User-Agent": f"Ma-Ru/{VERSION} (+{REPO})",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=20) as response:
            plugins = json.load(response)["plugins"]
        for entry in plugins:
            if entry.get("repo", "").lower().rstrip("/") == REPO.lower():
                return "PickAPlugin lists the source repository. Its editors refresh their public sources daily."
        return "PickAPlugin has not listed the repository yet. The initial email was submitted on November 26, 2026. Track its review without submitting duplicates."
    except (OSError, KeyError, ValueError, TypeError):
        return "PickAPlugin's public catalog could not be checked. Verify the repository link before contacting the editors."


if __name__ == "__main__":
    print(f"""[Release v{VERSION}]({release}) · [Distribution and review instructions]({REPO}/blob/v{VERSION}/docs/marketplaces.md)

- Claude Code and Codex read the bundled manifests from the repository. The release workflow checks both before building.
- ClawHub plugin and standalone skill publication each have a separate job. Check both jobs and their public verification.
- {pickaplugin()}
- [ ] Update the existing private Ma-Ru plugin through Plugin Creator using `ma-ru-{VERSION}.zip`. Confirm the version on the existing plugin.
- [ ] For an approved OpenAI desktop publisher, review changes and upload the new ZIP in the [submission portal](https://platform.openai.com/plugins) when required. Record the review or publication receipt. Keep this item pending if the organization has not been allowlisted.
""")
