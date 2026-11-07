import pytest

from tsuzuki.core.errors import ParseError
from tsuzuki.core.naming import episode_filename, folder_name


class TestFolderName:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Sousou no Frieren", "Sousou-no-Frieren"),
            ("Kaiju No. 8", "Kaiju-No-8"),
            ("  spaced   out  ", "spaced-out"),
            ("Re:Zero - Starting Life", "ReZero-Starting-Life"),
        ],
    )
    def test_keeps_letters_digits_and_single_dashes(self, title: str, expected: str) -> None:
        assert folder_name(title) == expected

    def test_path_tricks_are_flattened(self) -> None:
        name = folder_name("../../etc/passwd")
        assert "/" not in name and "." not in name

    def test_falls_back_when_nothing_is_left(self) -> None:
        assert folder_name("!!!") == "Unknown"
        assert folder_name("", fallback="Series") == "Series"


class TestEpisodeFilename:
    @pytest.mark.parametrize(
        ("number", "expected"),
        [("5", "episode_5.mp4"), ("12.5", "episode_12.5.mp4"), (" 7 ", "episode_7.mp4")],
    )
    def test_plain_numbers(self, number: str, expected: str) -> None:
        assert episode_filename(number) == expected

    def test_separators_are_removed(self) -> None:
        name = episode_filename("../x")
        assert "/" not in name and name == "episode_x.mp4"

    def test_extension_can_change(self) -> None:
        assert episode_filename("3", "mkv") == "episode_3.mkv"

    @pytest.mark.parametrize("number", ["", "   ", "...", "///"])
    def test_unusable_numbers_are_refused(self, number: str) -> None:
        with pytest.raises(ParseError):
            episode_filename(number)
