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


DATE_PATTERN = re.compile(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})")


def _extract_date_from_text(text: str) -> datetime.date | None:
    """텍스트에서 날짜 패턴을 찾아 추출합니다."""
    match = DATE_PATTERN.search(text)
    if match:
        try:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return datetime(year, month, day).date()
        except ValueError:
            pass
    return None


def _parse_date(date_text: str) -> datetime.date:
    """다양한 날짜 포맷을 파싱합니다."""
    text = date_text.strip()
    formats = [
        "%Y.%m.%d",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%y.%m.%d",
        "%y-%m-%d",
        "%m.%d",  # 올해로 가정
        "%m-%d",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
            # %m.%d 같은 경우 올해로 설정
            if parsed.year == 1900:
                parsed = parsed.replace(year=datetime.now().year)
            return parsed.date()
        except ValueError:
            continue
    raise ValueError(f"Unexpected date format: {date_text}")


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


def _find_notice_rows(soup: BeautifulSoup) -> List:
    """다양한 HTML 구조에서 공지 행을 찾습니다."""
    # 1) tbody > tr (기본)
    tbody = soup.find("tbody")
    if tbody:
        rows = tbody.find_all("tr")
        if rows:
            LOGGER.debug("Found %d rows in tbody", len(rows))
            return rows

    # 2) table > tr (tbody 없는 경우)
    table = soup.find("table", class_=lambda c: c and any(
        k in (c if isinstance(c, str) else " ".join(c))
        for k in ("board", "list", "notice", "bbs")
    ))
    if table:
        rows = table.find_all("tr")
        # 헤더 행 제외 (th가 있는 행)
        rows = [r for r in rows if not r.find("th")]
        if rows:
            LOGGER.debug("Found %d rows in table (no tbody)", len(rows))
            return rows

    # 3) ul.board-list > li 구조
    ul = soup.find("ul", class_=lambda c: c and any(
        k in (c if isinstance(c, str) else " ".join(c))
        for k in ("board", "list", "notice", "bbs")
    ))
    if ul:
        rows = ul.find_all("li")
        if rows:
            LOGGER.debug("Found %d items in ul list", len(rows))
            return rows

    # 4) div 기반 리스트
    div_list = soup.find("div", class_=lambda c: c and any(
        k in (c if isinstance(c, str) else " ".join(c))
        for k in ("board-list", "notice-list", "bbs-list")
    ))
    if div_list:
        rows = div_list.find_all("div", class_=lambda c: c and any(
            k in (c if isinstance(c, str) else " ".join(c))
            for k in ("item", "row", "tr")
        ))
        if rows:
            LOGGER.debug("Found %d items in div list", len(rows))
            return rows

    # 5) 최후의 수단: 모든 테이블에서 tr 찾기
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        rows = [r for r in rows if r.find("a", href=True) and not r.find("th")]
        if rows:
            LOGGER.debug("Found %d rows in fallback table search", len(rows))
            return rows

    LOGGER.warning("No notice rows found in any known HTML structure")
    return []


def parse_notices(html: str, base_url: str) -> List[Notice]:
    """Parse notice entries from HTML into Notice objects."""
    soup = BeautifulSoup(html, "html.parser")
    rows = _find_notice_rows(soup)

    if not rows:
        LOGGER.warning("No notice rows found in the HTML.")
        return []

    notices: list[Notice] = []
    for row in rows:
        link = row.find("a", href=True)
        if not link:
            LOGGER.debug("Skipping row without link: %s", row)
            continue

        href = link["href"].strip()
        notice_id = _extract_notice_id(href)
        if notice_id is None:
            LOGGER.warning("Failed to extract notice id from href: %s", href)
            continue

        # td 또는 span/div 등에서 정보 추출
        cells = row.find_all("td")
        if not cells:
            cells = row.find_all(["span", "div", "dd"])

        title = link.get_text(strip=True)
        url = urljoin(base_url, href)
        category = _extract_category(row, cells)
        writer = _extract_writer(cells) if cells else ""

        date_cell = _extract_date_cell(cells)
        date_value = None
        if date_cell:
            try:
                date_value = _parse_date(date_cell.get_text(strip=True))
            except ValueError:
                LOGGER.debug("Failed to parse date for notice %s", notice_id)

        # 날짜를 못 찾으면 row 전체 텍스트에서 날짜 패턴 찾기
        if date_value is None:
            date_value = _extract_date_from_text(row.get_text())

        if date_value is None:
            LOGGER.warning("Date not found for notice %s, using today", notice_id)
            date_value = datetime.now().date()

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
