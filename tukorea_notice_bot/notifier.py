"""Discord notification helpers."""

from __future__ import annotations

import logging
from typing import Iterable

import requests

from .models import Notice

LOGGER = logging.getLogger(__name__)


def send_discord_message(webhook_url: str, notice: Notice) -> None:
    """Send a single notice to Discord via webhook."""
    embed = {
        "title": f"[학사공지] {notice.title}",
        "url": notice.url,
        "description": f"{notice.category} · {notice.date.isoformat()} · {notice.writer}",
        "footer": {
            "text": f"조회수 {notice.views if notice.views is not None else 'N/A'} / 첨부파일 {'있음' if notice.has_attachment else '없음'}"
        },
    }
    response = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
    if not (200 <= response.status_code < 300):
        LOGGER.error("Discord webhook failed: %s - %s", response.status_code, response.text)
        response.raise_for_status()


def notify_new_notices(webhook_url: str, notices: Iterable[Notice]) -> None:
    """Send all new notices to Discord in chronological order."""
    for notice in notices:
        send_discord_message(webhook_url, notice)

