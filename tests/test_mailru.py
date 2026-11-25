import json
import secrets
from contextlib import nullcontext
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from ma_ru import accounts, remote, transport, wizard


@pytest.mark.parametrize("email", ["demo@mail.ru", "demo@bk.ru", "demo@custom.example"])
def test_provider_uses_tls_and_full_address(monkeypatch, email):
    imap = MagicMock()
    smtp = MagicMock()
    imap_factory = MagicMock(return_value=nullcontext(imap))
    smtp_factory = MagicMock(return_value=nullcontext(smtp))
    monkeypatch.setattr(transport, "IMAPClient", imap_factory)
    monkeypatch.setattr(transport.smtplib, "SMTP_SSL", smtp_factory)
    saved = []
    monkeypatch.setattr(transport, "save", saved.append)
    transport.connect(email, "fixture-with.punctuation", "send")
    assert saved[0].email == email
    imap.login.assert_called_once_with(email, saved[0].password)
    smtp.login.assert_called_once_with(email, saved[0].password)
    assert imap_factory.call_args.args == ("imap.mail.ru",)
    assert imap_factory.call_args.kwargs["port"] == 993
    assert imap_factory.call_args.kwargs["ssl_context"].check_hostname
    assert smtp_factory.call_args.args == ("smtp.mail.ru", 465)
    assert smtp_factory.call_args.kwargs["context"].check_hostname


def test_terminal_guides_to_mail_and_hides_password(monkeypatch):
    calls = []
    monkeypatch.setattr(wizard.sys.stdin, "isatty", lambda: True)
    answers = iter(["", "", "", "", "test@mail.ru", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(wizard.webbrowser, "open", calls.append)
    monkeypatch.setattr(wizard.getpass, "getpass", lambda _: "fixture")
    monkeypatch.setattr(wizard, "connect", lambda *args: calls.append(args))
    wizard.terminal()
    assert calls == [
        "https://id.mail.ru/contacts",
        "https://account.mail.ru/user/2-step-auth/passwords/",
        ("test@mail.ru", "fixture", "read"),
    ]


def test_http_requires_bearer_and_checks_origin():
    origin = "https://mail-agent.example.org"
    token = secrets.token_urlsafe(32)
    with pytest.raises(accounts.Problem):
        remote.application(origin, "")
    with pytest.raises(accounts.Problem):
        remote.application("http://mail-agent.example.org", token)
    headers = {"Accept": "application/json, text/event-stream"}
    with TestClient(remote.application(origin, token), base_url=origin) as client:
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        assert client.post("/mcp", headers=headers, json=request).status_code == 401
        headers["Authorization"] = "Bearer incorrect"
        assert client.post("/mcp", headers=headers, json=request).status_code == 401
        headers["Authorization"] = f"Bearer {token}"
        assert (
            client.post(
                "/mcp",
                headers={**headers, "Origin": "https://other.example.org"},
                json=request,
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/mcp", headers={**headers, "Host": "other.example.org"}, json=request
            ).status_code
            == 421
        )
        resp = client.post("/mcp", headers=headers, json=request)
        assert resp.status_code == 200
        assert any(t["name"] == "poll_new" for t in resp.json()["result"]["tools"])
        request.update(
            method="tools/call", params={"name": "list_accounts", "arguments": {}}
        )
        result = client.post("/mcp", headers=headers, json=request).json()["result"]
        assert (
            not result["isError"]
            and json.loads(result["content"][0]["text"])["accounts"] == []
        )
