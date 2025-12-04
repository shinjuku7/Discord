"""Fetch and parse notices from the Tukorea notice board."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import Notice

LOGGER = logging.getLogger(__name__)
NOTICE_ID_PATTERN = re.compile(r"/(\d+)/artclView\.do")


def fetch_html(url: str) -> str:
    """Retrieve the HTML contents of the given URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def _parse_date(date_text: str) -> datetime.date:
    try:
        return datetime.strptime(date_text.strip(), "%Y.%m.%d").date()
    except ValueError as exc:
        raise ValueError(f"Unexpected date format: {date_text}") from exc


def _parse_views(text: str) -> int | None:
    cleaned = text.replace(",", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


def _extract_category(row, cells) -> str:
    cell = row.find("td", class_=lambda c: c and ("category" in c or "cate" in c))
    if cell:
        return cell.get_text(strip=True)
    if len(cells) >= 2:
        return cells[1].get_text(strip=True)
    return ""


def _extract_writer(cells) -> str:
    for cell in cells:
        classes = cell.get("class", []) or []
        if any(key in cls for cls in classes for key in ("writer", "name")):
            return cell.get_text(strip=True)
    if len(cells) >= 3:
        return cells[-3].get_text(strip=True)
    return cells[-1].get_text(strip=True) if cells else ""


def _extract_date_cell(cells):
    for cell in cells:
        classes = cell.get("class", []) or []
        if any("date" in cls for cls in classes):
            return cell
    if len(cells) >= 2:
        return cells[-2]
    if cells:
        return cells[-1]
    return None


def _extract_views_cell(cells):
    for cell in cells:
        classes = cell.get("class", []) or []
        if any(key in cls for cls in classes for key in ("view", "hit")):
            return cell
    return cells[-1] if cells else None


def _has_attachment(row) -> bool:
    keywords = ("file", "첨부", "attach")
    for tag in row.find_all(["img", "span", "i"]):
        alt = (tag.get("alt") or "").lower()
        title = (tag.get("title") or "").lower()
        classes = " ".join(tag.get("class", [])).lower()
        text = tag.get_text(strip=True).lower()
        if any(key in alt for key in keywords):
            return True
        if any(key in title for key in keywords):
            return True
        if any(key in classes for key in keywords):
            return True
        if any(key in text for key in keywords):
            return True
    return False


def parse_notices(html: str, base_url: str) -> List[Notice]:
    """Parse notice entries from HTML into Notice objects."""
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.find("tbody")
    if not tbody:
        LOGGER.warning("No <tbody> found in the notice list HTML.")
        return []

    notices: list[Notice] = []
    for row in tbody.find_all("tr"):
        link = row.find("a", href=True)
        if not link:
            LOGGER.debug("Skipping row without link: %s", row)
            continue

        href = link["href"].strip()
        id_match = NOTICE_ID_PATTERN.search(href)
        if not id_match:
            LOGGER.warning("Failed to extract notice id from href: %s", href)
            continue
        notice_id = id_match.group(1)

        cells = row.find_all("td")
        title = link.get_text(strip=True)
        url = urljoin(base_url, href)
        category = _extract_category(row, cells)
        writer = _extract_writer(cells)

        date_cell = _extract_date_cell(cells)
        if not date_cell:
            raise ValueError(f"Date cell missing for notice {notice_id}")
        date_value = _parse_date(date_cell.get_text(strip=True))

        views_cell = _extract_views_cell(cells)
        views_value = _parse_views(views_cell.get_text(strip=True)) if views_cell else None
        has_attachment = _has_attachment(row)

        notices.append(
            Notice(
                id=notice_id,
                title=title,
                url=url,
                category=category,
                writer=writer,
                date=date_value,
                views=views_value,
                has_attachment=has_attachment,
            )
        )

    return notices


def get_latest_notices(list_url: str) -> List[Notice]:
    """Fetch and parse the first page of the notice list."""
    html = fetch_html(list_url)
    return parse_notices(html, list_url)
