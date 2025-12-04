import json
from datetime import date

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
