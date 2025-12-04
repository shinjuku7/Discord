"""State management for previously seen notices."""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable, Set

from .models import Notice

LOGGER = logging.getLogger(__name__)


def load_seen_ids(path: str = "state.json") -> Set[str]:
    """Load seen notice IDs from a JSON file."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid state file: {path}") from exc

    seen_ids = data.get("seen_ids", [])
    return {str(item) for item in seen_ids}


def save_seen_ids(seen_ids: Set[str], path: str = "state.json", max_size: int = 500) -> None:
    """Persist seen IDs to disk, limiting the size of the list."""
    try:
        max_size_int = int(max_size)
    except (TypeError, ValueError):
        LOGGER.warning("Invalid max_size %s, falling back to 500", max_size)
        max_size_int = 500

    ordered_ids = sorted(seen_ids, reverse=True)[:max_size_int]
    payload = {"seen_ids": ordered_ids}

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def diff_new_notices(notices: list[Notice], seen_ids: Set[str]) -> list[Notice]:
    """Return notices that are not in the seen_id set, oldest first."""
    new_notices = [notice for notice in notices if notice.id not in seen_ids]
    return sorted(new_notices, key=lambda n: (n.date, n.id))

