from unittest.mock import MagicMock

import pytest
from imapclient.response_types import BodyData

from ma_ru import accounts, mail, outbox, server


def test_edit_replays_even_after_original_moved(env):
    a, box = env
    letter = outbox.Letter(
        to=["reader@example.net"], subject="договор", text="версия 1"
    )
    original = mail.Ref(**server.create_draft(a.email, letter)["ref"])
    new = letter.model_copy(update={"text": "версия 2"})
    updated = server.update_draft(original, new)
    assert updated["original"] == "moved_to_trash"
    assert server.update_draft(original, new) == updated
    assert len(box.data["Trash"]) == len(box.data["Drafts"]) == 1
    assert "версия 2" in server.read_message(mail.Ref(**updated["ref"]))["body"]
    with pytest.raises(accounts.Problem):
        server.update_draft(original, letter)


def test_edit_failed_cleanup_preserves_both_and_does_not_repeat(env, monkeypatch):
    a, box = env
    letter = outbox.Letter(subject="test", text="original")
    original = mail.Ref(**server.create_draft(a.email, letter)["ref"])
    monkeypatch.setattr(box, "move", MagicMock(side_effect=OSError()))
    updated = server.update_draft(original, letter)
    assert updated["original"] == "check_original"
    assert len(box.data["Drafts"]) == 2
    assert server.update_draft(original, letter) == updated
    assert box.move.call_count == 1


def test_attachment_search_uses_only_bodystructure():
    plain = (b"TEXT", b"PLAIN", None, None, None, b"7BIT", 5, 1)
    pdf = (
        b"APPLICATION",
        b"PDF",
        None,
        None,
        None,
        b"BASE64",
        5,
        None,
        (b"ATTACHMENT", None),
    )
    multi = BodyData.create((plain, pdf, b"MIXED"))
    assert not mail.has_attachment(BodyData.create(plain))
    assert mail.has_attachment(multi)
    box = MagicMock()
    box.fetch.return_value = {
        1: {b"BODYSTRUCTURE": BodyData.create(plain)},
        2: {b"BODYSTRUCTURE": multi},
    }
    assert list(mail.filter_attachments(box, [1, 2], True)) == [2]
    box.fetch.assert_called_once_with((1, 2), ["BODYSTRUCTURE"])
    assert mail.Filter(cc="team@example.org", larger_than=1000).criteria() == [
        "UNDELETED",
        "CC",
        "team@example.org",
        "LARGER",
        "1000",
    ]
