from pathlib import Path

from tsuzuki.core.models import DownloadJob, MediaSource
from tsuzuki.download.aria2 import build_command, header_args


def job(headers: dict[str, str] | None = None) -> DownloadJob:
    source = MediaSource("https://cdn.example/v.mp4", headers or {})
    return DownloadJob(source, Path("/d/Show"), "episode_1.mp4")


class TestHeaderArgs:
    def test_user_agent_and_referer_get_their_own_options(self) -> None:
        args = header_args({"User-Agent": "UA", "Referer": "https://r/"})
        assert args == ["--user-agent", "UA", "--referer", "https://r/"]

    def test_other_headers_are_passed_through(self) -> None:
        assert header_args({"Cookie": "a=b"}) == ["--header", "Cookie: a=b"]


class TestBuildCommand:
    def test_resumes_and_never_renames(self) -> None:
        command = build_command(job())
        assert "-c" in command
        assert "--allow-overwrite=true" in command
        assert "--auto-file-renaming=false" in command

    def test_where_the_file_goes_and_what_it_is_called(self) -> None:
        command = build_command(job())
        assert command[command.index("-d") + 1] == str(Path("/d/Show"))
        assert command[command.index("-o") + 1] == "episode_1.mp4"
        assert command[-1] == "https://cdn.example/v.mp4"

    def test_connection_count(self) -> None:
        command = build_command(job(), connections=4)
        assert command[command.index("-x") + 1] == "4"
        assert command[command.index("-s") + 1] == "4"
