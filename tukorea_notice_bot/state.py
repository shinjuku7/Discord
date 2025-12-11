# state.py
"""이미 본 공지 ID들을 관리하는 모듈."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Collection, List, Optional, Set

from .models import Notice

LOGGER = logging.getLogger(__name__)

# 프로젝트 루트의 state.json을 기본으로 사용해 기존 동작과 호환 유지
STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"


def load_seen_ids(path: str | Path | None = None) -> Set[str]:
    """state.json에서 이미 본 공지 ID 집합을 읽어옵니다."""
    state_path = Path(path) if path is not None else STATE_PATH
    try:
        raw = state_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        LOGGER.info("state.json 없음 -> 빈 seen_ids로 시작")
        return set()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        LOGGER.warning("state.json 파싱 실패 -> 초기화")
        return set()

    ids = data.get("seen_ids", [])
    # 전부 문자열로 맞추기
    return {str(x).strip() for x in ids}


def save_seen_ids(
    seen_ids: Iterable[str], *, path: str | Path | None = None, max_size: int = 100
) -> None:
    """seen_ids를 state.json에 저장합니다. 너무 많으면 최신 ID 위주로 자릅니다."""
    ids_set = {str(x).strip() for x in seen_ids}
    state_path = Path(path) if path is not None else STATE_PATH

    # 숫자로 정렬이 가능하면 숫자 기준 내림차순
    try:
        sorted_ids = sorted(ids_set, key=lambda x: int(x), reverse=True)
    except ValueError:
        sorted_ids = sorted(ids_set, reverse=True)

    trimmed = sorted_ids[:max_size]

    data = {"seen_ids": trimmed}
    state_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LOGGER.info("state.json 저장 완료, 총 %d개 id", len(trimmed))


def diff_new_notices(
    notices: List[Notice],
    seen_ids: Collection[str],
    *,
    filter_by_date: bool = False,
    date_range_days: int = 1,
    reference_date: Optional[date] = None,
) -> List[Notice]:
    """공지 리스트에서 '새로운' 공지만 골라냅니다.

    Args:
        notices: 크롤링한 공지 리스트
        seen_ids: 이미 본 공지 ID 집합
        filter_by_date: True면 날짜 기반 필터링도 적용
        date_range_days: 오늘로부터 며칠 이내 공지만 포함 (기본 1일)
        reference_date: 기준 날짜 (기본값: 오늘)

    Returns:
        새 공지 리스트 (ID 오름차순 정렬)
    """
    seen = {str(x).strip() for x in seen_ids}
    today = reference_date or date.today()
    cutoff_date = today - timedelta(days=date_range_days - 1)

    new_list: List[Notice] = []
    for n in notices:
        notice_id = str(n.id).strip()

        # seen_ids 체크
        if notice_id in seen:
            LOGGER.debug("공지 ID %s: 이미 본 공지 -> 스킵", notice_id)
            continue

        # 날짜 필터링 (옵션)
        if filter_by_date and n.date < cutoff_date:
            LOGGER.debug(
                "공지 ID %s: 날짜 %s가 기준일 %s 이전 -> 스킵",
                notice_id,
                n.date,
                cutoff_date,
            )
            continue

        LOGGER.debug(
            "공지 ID %s: 새 공지로 인식 (제목: %s, 날짜: %s)",
            notice_id,
            n.title[:20] if len(n.title) > 20 else n.title,
            n.date,
        )
        new_list.append(n)

    # 오래된 것부터 보내고 싶으면 ID 오름차순으로 정렬
    try:
        new_list.sort(key=lambda n: int(str(n.id)))
    except ValueError:
        pass

    LOGGER.info(
        "전체 공지 %d개, seen_ids %d개, 새 공지 %d개 (날짜필터=%s, 기준일=%s)",
        len(notices),
        len(seen),
        len(new_list),
        filter_by_date,
        cutoff_date if filter_by_date else "N/A",
    )

    return new_list
