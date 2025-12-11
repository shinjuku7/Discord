# tukorea_notice_bot/notifier.py

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Iterable

import requests

from .models import Notice

LOGGER = logging.getLogger(__name__)


def _post_with_rate_limit(webhook_url: str, payload: dict) -> None:
    """디스코드 웹훅에 전송하되, 429가 나오면 기다렸다가 재시도."""
    while True:
        resp = requests.post(webhook_url, json=payload, timeout=10)

        # 레이트 리밋
        if resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 1.0))
            except Exception:
                retry_after = 1.0
            LOGGER.warning("디스코드 레이트 리밋, %.1f초 대기", retry_after)
            time.sleep(retry_after)
            continue  # 다시 시도

        # 그 외 오류는 예외로 처리
        resp.raise_for_status()
        return


def _build_embed(notice: Notice) -> dict:
    """공지 정보를 디스코드 임베드 형태로 변환."""
    title_prefix = "학사공지"
    embed = {
        "title": f"[{title_prefix}] {notice.title}",
        "url": notice.url,
        "description": _build_description(notice),
        "footer": {"text": _build_footer(notice)},
    }
    return embed


def _build_description(notice: Notice) -> str:
    parts = [
        f"분류: {notice.category}",
        f"작성자: {notice.writer}",
        f"게시일: {_format_date(notice.date)}",
    ]

    if notice.has_attachment:
        parts.append("첨부 파일 있음")

    return "\n".join(parts)


def _build_footer(notice: Notice) -> str:
    if notice.views is None:
        return "조회수 정보 없음"
    return f"조회수 {notice.views}"


def _format_date(value: date) -> str:
    return value.isoformat()


def send_discord_message(webhook_url: str, notice: Notice) -> None:
    """단일 공지를 디스코드 웹훅으로 전송."""
    payload = {
        "allowed_mentions": {"parse": []},  # 멘션 방지
        "embeds": [_build_embed(notice)],
    }

    _post_with_rate_limit(webhook_url, payload)
    LOGGER.info("디스코드 전송 완료: %s (%s)", notice.id, notice.title)


def notify_new_notices(webhook_url: str, notices: Iterable[Notice]) -> None:
    """새 공지들을 디스코드로 전송."""
    for notice in notices:
        send_discord_message(webhook_url, notice)
        time.sleep(0.2)  # 너무 빠르게 연속 호출하지 않도록 약간 쉬어줌
