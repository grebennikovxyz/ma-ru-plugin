import hashlib
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import clawhub_release as release
import marketplace_versions


def test_checkout_matches_marketplaces():
    marketplace_versions.synchronize()


@pytest.mark.parametrize("channel", ["package", "skill"])
def test_retry_verifies_the_existing_public_artifact(channel, tmp_path, monkeypatch):
    skill = tmp_path / "SKILL.md"
    skill.write_bytes(b"example")
    digest = hashlib.sha256(skill.read_bytes()).hexdigest()
    monkeypatch.setattr(release, "SKILL", tmp_path)
    data = (
        {
            "version": {
                "version": release.VERSION,
                "files": [{"path": "SKILL.md", "sha256": digest}],
            }
        }
        if channel == "skill"
        else {
            "version": release.VERSION,
            "package": {"name": release.PACKAGE},
            "artifact": {"sha256": digest},
        }
    )
    monkeypatch.setattr(release, "read_json", lambda url: data)
    assert release.published(channel, skill)
    skill.write_bytes(b"changed")
    with pytest.raises(SystemExit, match="different content"):
        release.published(channel, skill)


def test_only_http_404_means_absent(monkeypatch, tmp_path):
    for code in (404, 403, 503):

        def unavailable(url, status=code):
            raise HTTPError(url, status, "", None, None)

        monkeypatch.setattr(release, "read_json", unavailable)
        if code == 404:
            assert not release.published("skill", tmp_path)
        else:
            with pytest.raises(HTTPError):
                release.published("skill", tmp_path)
