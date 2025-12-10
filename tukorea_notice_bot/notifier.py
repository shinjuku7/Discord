# tukorea_notice_bot/notifier.py

from __future__ import annotations

import logging
import time
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


def notify_new_notices(webhook_url: str, notices: Iterable[Notice]) -> None:
    """새 공지들을 디스코드로 전송."""
    for notice in notices:
        content = f"[{notice.category}] {notice.title}\n{notice.url}"
        payload = {
            "content": content,
            "allowed_mentions": {"parse": []},  # 멘션 방지
        }

        _post_with_rate_limit(webhook_url, payload)
        time.sleep(0.2)  # 너무 빠르게 연속 호출하지 않도록 약간 쉬어줌
        LOGGER.info("디스코드 전송 완료: %s (%s)", notice.id, notice.title)
