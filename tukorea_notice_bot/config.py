"""Configuration handling for the notice bot."""

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


DEFAULT_NOTICE_LIST_URL = "https://www.tukorea.ac.kr/tukorea/7607/subview.do"
DEFAULT_MAX_SEEN_IDS = 500
DEFAULT_FILTER_BY_DATE = True
DEFAULT_DATE_RANGE_DAYS = 1


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    discord_webhook_url: str
    notice_list_url: str = DEFAULT_NOTICE_LIST_URL
    max_seen_ids: int = DEFAULT_MAX_SEEN_IDS
    filter_by_date: bool = DEFAULT_FILTER_BY_DATE
    date_range_days: int = DEFAULT_DATE_RANGE_DAYS


def get_settings() -> Settings:
    """Load settings from environment variables, raising on missing webhook."""
    if load_dotenv is not None:
        load_dotenv()

    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise ValueError("DISCORD_WEBHOOK_URL is required")

    list_url = os.getenv("NOTICE_LIST_URL", DEFAULT_NOTICE_LIST_URL)

    max_seen_raw = os.getenv("MAX_SEEN_IDS", str(DEFAULT_MAX_SEEN_IDS))
    try:
        max_seen = int(max_seen_raw)
    except ValueError as exc:
        raise ValueError("MAX_SEEN_IDS must be an integer") from exc

    # 날짜 필터링 설정
    filter_by_date_raw = os.getenv("FILTER_BY_DATE", str(DEFAULT_FILTER_BY_DATE))
    filter_by_date = filter_by_date_raw.lower() in ("true", "1", "yes")

    date_range_raw = os.getenv("DATE_RANGE_DAYS", str(DEFAULT_DATE_RANGE_DAYS))
    try:
        date_range_days = int(date_range_raw)
    except ValueError as exc:
        raise ValueError("DATE_RANGE_DAYS must be an integer") from exc

    return Settings(
        discord_webhook_url=webhook.strip(),
        notice_list_url=list_url.strip(),
        max_seen_ids=max_seen,
        filter_by_date=filter_by_date,
        date_range_days=date_range_days,
    )

