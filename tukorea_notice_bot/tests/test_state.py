import json
from datetime import date, timedelta

from tukorea_notice_bot.models import Notice
from tukorea_notice_bot.state import diff_new_notices, load_seen_ids, save_seen_ids


def test_save_and_load_seen_ids(tmp_path):
    path = tmp_path / "state.json"
    seen = {"100", "200", "150"}

    save_seen_ids(seen, path=str(path), max_size=2)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["seen_ids"] == ["200", "150"]

    loaded = load_seen_ids(str(path))
    assert loaded == {"200", "150"}


def test_diff_new_notices_filters_seen():
    notices = [
        Notice(
            id="1",
            title="old",
            url="http://example.com/1",
            category="일반공지",
            writer="writer",
            date=date(2024, 1, 1),
            views=None,
            has_attachment=False,
        ),
        Notice(
            id="3",
            title="new",
            url="http://example.com/3",
            category="일반공지",
            writer="writer",
            date=date(2024, 1, 2),
            views=10,
            has_attachment=False,
        ),
    ]
    seen_ids = {"1", "2"}

    new_notices = diff_new_notices(notices, seen_ids)

    assert [notice.id for notice in new_notices] == ["3"]


def test_diff_new_notices_with_date_filter_includes_today():
    """오늘 날짜 공지는 필터링되지 않아야 함."""
    today = date.today()
    notices = [
        Notice(
            id="100",
            title="오늘 공지",
            url="http://example.com/100",
            category="일반공지",
            writer="writer",
            date=today,
            views=None,
            has_attachment=False,
        ),
        Notice(
            id="101",
            title="어제 공지",
            url="http://example.com/101",
            category="일반공지",
            writer="writer",
            date=today - timedelta(days=1),
            views=None,
            has_attachment=False,
        ),
        Notice(
            id="102",
            title="오래된 공지",
            url="http://example.com/102",
            category="일반공지",
            writer="writer",
            date=today - timedelta(days=10),
            views=None,
            has_attachment=False,
        ),
    ]
    seen_ids = set()

    # 날짜 필터 OFF -> 모든 새 공지 포함
    new_notices = diff_new_notices(notices, seen_ids, filter_by_date=False)
    assert [n.id for n in new_notices] == ["100", "101", "102"]

    # 날짜 필터 ON (1일) -> 오늘만 포함
    new_notices = diff_new_notices(
        notices, seen_ids, filter_by_date=True, date_range_days=1, reference_date=today
    )
    assert [n.id for n in new_notices] == ["100"]

    # 날짜 필터 ON (2일) -> 오늘, 어제 포함
    new_notices = diff_new_notices(
        notices, seen_ids, filter_by_date=True, date_range_days=2, reference_date=today
    )
    assert [n.id for n in new_notices] == ["100", "101"]


def test_diff_new_notices_date_filter_respects_seen_ids():
    """날짜 필터가 켜져 있어도 seen_ids는 여전히 체크해야 함."""
    today = date.today()
    notices = [
        Notice(
            id="200",
            title="오늘 공지 (이미 봄)",
            url="http://example.com/200",
            category="일반공지",
            writer="writer",
            date=today,
            views=None,
            has_attachment=False,
        ),
        Notice(
            id="201",
            title="오늘 공지 (새 공지)",
            url="http://example.com/201",
            category="일반공지",
            writer="writer",
            date=today,
            views=None,
            has_attachment=False,
        ),
    ]
    seen_ids = {"200"}

    new_notices = diff_new_notices(
        notices, seen_ids, filter_by_date=True, date_range_days=1, reference_date=today
    )
    # id=200은 이미 봤으므로 제외, id=201만 포함
    assert [n.id for n in new_notices] == ["201"]
