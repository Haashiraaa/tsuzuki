import argparse

import pytest

from tsuzuki.cli.args import parse_args, positive_int, retry_from, selection_from
from tsuzuki.core.models import Selection


class TestPositiveInt:
    def test_accepts_one_and_up(self) -> None:
        assert positive_int("1") == 1
        assert positive_int("25") == 25

    @pytest.mark.parametrize("text", ["0", "-3", "abc", "1.5", ""])
    def test_rejects_everything_else(self, text: str) -> None:
        with pytest.raises(argparse.ArgumentTypeError):
            positive_int(text)


class TestParse:
    def test_defaults(self) -> None:
        args = parse_args(["--urls", "https://x.example/a"])
        assert args.urls == ["https://x.example/a"]
        assert (args.workers, args.retries, args.debug, args.output) == (3, 5, False, None)
        assert selection_from(args) == Selection()

    def test_several_urls(self) -> None:
        assert len(parse_args(["--urls", "https://a/", "https://b/"]).urls) == 2

    def test_urls_are_required(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as stop:
            parse_args([])
        assert stop.value.code == 2
        assert "--urls" in capsys.readouterr().err

    def test_episode_and_limit_cannot_be_combined(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--urls", "u", "--episode", "1", "--limit", "2"])

    @pytest.mark.parametrize("flag", ["--episode", "--limit", "--workers", "--retries"])
    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_numbers_must_be_positive(self, flag: str, value: str) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--urls", "u", flag, value])

    def test_selection_options(self) -> None:
        args = parse_args(["--urls", "u", "--limit", "3", "--oldest"])
        assert selection_from(args) == Selection(limit=3, newest_first=False)

    def test_retry_policy(self) -> None:
        assert retry_from(parse_args(["--urls", "u", "--retries", "2"])).attempts == 2

    def test_version_flag_exits_cleanly(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as stop:
            parse_args(["--version"])
        assert stop.value.code == 0
        assert capsys.readouterr().out.startswith("tsuzuki ")
