# state.py
"""이미 본 공지 ID들을 관리하는 모듈."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Collection, List, Set

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
) -> List[Notice]:
    """공지 리스트에서 '새로운' 공지만 골라냅니다."""
    seen = {str(x).strip() for x in seen_ids}

    # 아직 seen_ids에 없는 것만 새 공지로 인식
    new_list = [n for n in notices if str(n.id).strip() not in seen]

    # 오래된 것부터 보내고 싶으면 ID 오름차순으로 정렬
    try:
        new_list.sort(key=lambda n: int(str(n.id)))
    except ValueError:
        pass

    LOGGER.info(
        "전체 공지 %d개 중 새 공지 %d개",
        len(notices),
        len(new_list),
    )

    return new_list
