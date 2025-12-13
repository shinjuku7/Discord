"""Fetch and parse notices from the Tukorea notice board."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List
from urllib.parse import parse_qs, urljoin, urlparse

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


def _extract_notice_id(href: str) -> str | None:
    """Extract notice id from various href formats.

    Supports the legacy `/123/artclView.do` pattern as well as query strings like
    `artclView.do?article=123` or `artclView.do?idx=123`.
    """

    parsed = urlparse(href)

    # 1) query string values
    query_params = parse_qs(parsed.query)
    for key, values in query_params.items():
        lowered = key.lower()
        if any(token in lowered for token in ("artcl", "article", "id", "idx", "no", "seq")):
            for value in values:
                candidate = value.strip()
                if candidate.isdigit():
                    return candidate

    # 2) original /<id>/artclView.do pattern
    match = NOTICE_ID_PATTERN.search(href)
    if match:
        return match.group(1)

    # 3) trailing path segments
    digit_segments = [seg for seg in parsed.path.split("/") if seg.isdigit()]
    if digit_segments:
        # pick the longest numeric segment to avoid board ids like "107"
        return max(digit_segments, key=len)

    return None


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

    # 새 구조: ul.list-normal > li
    ul = soup.find("ul", class_="list-normal")
    if ul:
        return _parse_list_normal(ul, base_url)

    # 기존 구조: tbody > tr (fallback)
    tbody = soup.find("tbody")
    if tbody:
        return _parse_tbody(tbody, base_url)

    LOGGER.warning("No <ul class='list-normal'> or <tbody> found in HTML.")
    return []


def _parse_list_normal(ul, base_url: str) -> List[Notice]:
    """Parse notices from ul.list-normal structure."""
    notices: list[Notice] = []

    for li in ul.find_all("li"):
        link = li.find("a", href=True)
        if not link:
            continue

        href = link["href"].strip()
        notice_id = _extract_notice_id(href)
        if notice_id is None:
            LOGGER.warning("Failed to extract notice id from href: %s", href)
            continue

        # 제목: .title strong
        title_tag = li.find("div", class_="title")
        title = ""
        if title_tag:
            strong = title_tag.find("strong")
            title = strong.get_text(strip=True) if strong else title_tag.get_text(strip=True)

        url = urljoin(base_url, href)

        # desc 영역에서 정보 추출
        desc = li.find("div", class_="desc")
        writer = ""
        date_value = None
        views_value = None

        if desc:
            # 작성자: dl.writer dd
            writer_dl = desc.find("dl", class_="writer")
            if writer_dl:
                dd = writer_dl.find("dd")
                writer = dd.get_text(strip=True) if dd else ""

            # 날짜: dl.date dd
            date_dl = desc.find("dl", class_="date")
            if date_dl:
                dd = date_dl.find("dd")
                if dd:
                    date_value = _parse_date(dd.get_text(strip=True))

            # 조회수: dl.count dd
            count_dl = desc.find("dl", class_="count")
            if count_dl:
                dd = count_dl.find("dd")
                if dd:
                    views_value = _parse_views(dd.get_text(strip=True))

            # 첨부파일: span.file-count
            file_count = desc.find("span", class_="file-count")
            has_attachment = False
            if file_count:
                count_text = file_count.get_text(strip=True)
                has_attachment = count_text.isdigit() and int(count_text) > 0
        else:
            has_attachment = False

        if date_value is None:
            LOGGER.warning("Date missing for notice %s, skipping", notice_id)
            continue

        notices.append(
            Notice(
                id=notice_id,
                title=title,
                url=url,
                category="",
                writer=writer,
                date=date_value,
                views=views_value,
                has_attachment=has_attachment,
            )
        )

    return notices


def _parse_tbody(tbody, base_url: str) -> List[Notice]:
    """Parse notices from tbody > tr structure (legacy)."""
    notices: list[Notice] = []

    for row in tbody.find_all("tr"):
        link = row.find("a", href=True)
        if not link:
            LOGGER.debug("Skipping row without link: %s", row)
            continue

        href = link["href"].strip()
        notice_id = _extract_notice_id(href)
        if notice_id is None:
            LOGGER.warning("Failed to extract notice id from href: %s", href)
            continue

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
