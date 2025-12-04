from datetime import date

from tukorea_notice_bot.crawler import parse_notices


SAMPLE_HTML = """
<table class="board-list">
  <tbody>
    <tr>
      <td class="no">공지</td>
      <td class="category">일반공지</td>
      <td class="title">
        <a href="/bbs/tukorea/107/145435/artclView.do">첫 번째 공지</a>
        <span class="ico-file">첨부</span>
      </td>
      <td class="writer">교무팀</td>
      <td class="date">2024.05.01</td>
      <td class="views">123</td>
    </tr>
    <tr>
      <td class="no">2</td>
      <td class="category">장학공지</td>
      <td class="title">
        <a href="/bbs/tukorea/107/145434/artclView.do">두 번째 공지</a>
      </td>
      <td class="writer">학생지원팀</td>
      <td class="date">2024.04.30</td>
      <td class="views">-</td>
    </tr>
  </tbody>
</table>
"""


def test_parse_notices_extracts_fields():
    base_url = "https://www.tukorea.ac.kr"

    notices = parse_notices(SAMPLE_HTML, base_url)

    assert len(notices) == 2

    first, second = notices

    assert first.id == "145435"
    assert first.title == "첫 번째 공지"
    assert (
        first.url
        == "https://www.tukorea.ac.kr/bbs/tukorea/107/145435/artclView.do"
    )
    assert first.category == "일반공지"
    assert first.writer == "교무팀"
    assert first.date == date(2024, 5, 1)
    assert first.views == 123
    assert first.has_attachment is True

    assert second.id == "145434"
    assert second.title == "두 번째 공지"
    assert (
        second.url
        == "https://www.tukorea.ac.kr/bbs/tukorea/107/145434/artclView.do"
    )
    assert second.category == "장학공지"
    assert second.writer == "학생지원팀"
    assert second.date == date(2024, 4, 30)
    assert second.views is None
    assert second.has_attachment is False

