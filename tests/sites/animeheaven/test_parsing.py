import pytest

from tsuzuki.core.errors import ParseError
from tsuzuki.sites.animeheaven.parsing import (
    make_soup,
    parse_episodes,
    parse_title,
    parse_video_url,
)

SERIES_PAGE = """
<html><head>
  <meta property="og:title" content="  Sample Show  ">
  <title>Sample Show - AnimeHeaven</title>
</head><body>
  <a href="gate.php" id="ref12"><div class="watch2">12</div></a>
  <a href="gate.php" id="ref11"><div class="watch2">11</div></a>
  <a href="other.php" id="nope"><div class="watch2">99</div></a>
</body></html>
"""

EPISODE_PAGE = '<video><source src="/media/ep12.mp4"></video>'


class TestTitle:
    def test_prefers_the_social_title(self) -> None:
        assert parse_title(make_soup(SERIES_PAGE)) == "Sample Show"

    def test_falls_back_to_the_page_title(self) -> None:
        soup = make_soup("<html><head><title>Only Title</title></head></html>")
        assert parse_title(soup) == "Only Title"

    def test_no_title_at_all_is_an_error(self) -> None:
        with pytest.raises(ParseError, match="title"):
            parse_title(make_soup("<html><body>nothing</body></html>"))


class TestEpisodes:
    def test_lists_episodes_in_page_order(self) -> None:
        episodes = parse_episodes(make_soup(SERIES_PAGE))
        assert [(e.number, e.ref) for e in episodes] == [("12", "ref12"), ("11", "ref11")]

    def test_no_episodes_is_an_error(self) -> None:
        with pytest.raises(ParseError, match="No episodes"):
            parse_episodes(make_soup("<html><body></body></html>"))

    def test_a_link_missing_its_number_is_an_error(self) -> None:
        with pytest.raises(ParseError, match="missing"):
            parse_episodes(make_soup('<a href="gate.php" id="x"><div class="watch2"></div></a>'))


class TestVideo:
    def test_relative_sources_are_made_absolute(self) -> None:
        url = parse_video_url(make_soup(EPISODE_PAGE), "https://animeheaven.me/gate.php")
        assert url == "https://animeheaven.me/media/ep12.mp4"

    def test_video_tag_with_its_own_src(self) -> None:
        soup = make_soup('<video src="https://cdn.example/v.mp4"></video>')
        assert parse_video_url(soup, "https://animeheaven.me/") == "https://cdn.example/v.mp4"

    def test_no_video_is_an_error(self) -> None:
        with pytest.raises(ParseError, match="video"):
            parse_video_url(make_soup("<p>nothing</p>"), "https://animeheaven.me/")
