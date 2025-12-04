"""Entrypoint for the Tukorea notice Discord notifier."""

from __future__ import annotations

import logging
import os
import sys

from requests.exceptions import RequestException

try:
    from .config import get_settings
    from .crawler import get_latest_notices
    from .notifier import notify_new_notices
    from .state import diff_new_notices, load_seen_ids, save_seen_ids
except ImportError:  # pragma: no cover - fallback when executed as a script
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import get_settings
    from crawler import get_latest_notices
    from notifier import notify_new_notices
    from state import diff_new_notices, load_seen_ids, save_seen_ids

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Run the notifier workflow."""
    try:
        settings = get_settings()
    except ValueError as exc:
        LOGGER.error("Configuration error: %s", exc)
        return 1

    seen_ids = load_seen_ids()

    try:
        notices = get_latest_notices(settings.notice_list_url)
    except RequestException as exc:
        LOGGER.error("Failed to fetch notices: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to parse notices: %s", exc)
        return 1

    new_notices = diff_new_notices(notices, seen_ids)
    if not new_notices:
        LOGGER.info("새 공지 0개, 아무것도 안 함")
        return 0

    try:
        notify_new_notices(settings.discord_webhook_url, new_notices)
    except RequestException as exc:
        LOGGER.error("Failed to send Discord notification: %s", exc)
        return 1

    updated_seen = set(seen_ids)
    updated_seen.update(notice.id for notice in new_notices)
    save_seen_ids(updated_seen, max_size=settings.max_seen_ids)

    LOGGER.info("새 공지 %d개, 디스코드로 전송 완료", len(new_notices))
    return 0


if __name__ == "__main__":
    sys.exit(main())
