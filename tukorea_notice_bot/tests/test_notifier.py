from datetime import date

from tukorea_notice_bot.models import Notice
from tukorea_notice_bot import notifier


class DummyResponse:
    def __init__(self, status_code: int = 204):
        self.status_code = status_code
        self.text = ""

    def raise_for_status(self) -> None:
        return None


def test_send_discord_message_builds_payload(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return DummyResponse()

    monkeypatch.setattr(notifier.requests, "post", fake_post)

    notice = Notice(
        id="1",
        title="테스트 공지",
        url="https://example.com/notice/1",
        category="일반공지",
        writer="관리자",
        date=date(2024, 5, 1),
        views=42,
        has_attachment=True,
    )

    webhook_url = "https://example.com/webhook"
    notifier.send_discord_message(webhook_url, notice)

    assert captured["url"] == webhook_url
    embed = captured["json"]["embeds"][0]
    assert embed["title"] == "[학사공지] 테스트 공지"
    assert embed["url"] == "https://example.com/notice/1"
    assert "일반공지" in embed["description"]
    assert "조회수 42" in embed["footer"]["text"]


def test_notify_new_notices_sends_in_order(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        title = json["embeds"][0]["title"]
        calls.append(title)
        return DummyResponse()

    monkeypatch.setattr(notifier.requests, "post", fake_post)

    notices = [
        Notice(
            id="1",
            title="첫 공지",
            url="https://example.com/1",
            category="일반공지",
            writer="관리자",
            date=date(2024, 5, 1),
            views=None,
            has_attachment=False,
        ),
        Notice(
            id="2",
            title="둘째 공지",
            url="https://example.com/2",
            category="장학공지",
            writer="관리자",
            date=date(2024, 5, 2),
            views=None,
            has_attachment=False,
        ),
    ]

    notifier.notify_new_notices("https://example.com/webhook", notices)

    assert calls == ["[학사공지] 첫 공지", "[학사공지] 둘째 공지"]

