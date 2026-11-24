import sys
import textwrap
import time
from pathlib import Path

import pytest

from tsuzuki.core.errors import DownloadError
from tsuzuki.core.events import ProgressEvent
from tsuzuki.core.models import DownloadJob, MediaSource
from tsuzuki.download.aria2 import (
    build_command,
    header_args,
    parse_readout,
    run_aria2_captured,
)


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


class TestParseReadout:
    def test_reads_done_and_total_from_a_readout_line(self) -> None:
        line = "[#2089b0 400KiB/33MiB(1%) CN:1 DL:115KiB ETA:4m51s]"
        event = parse_readout(line, "episode_1.mp4")
        assert event == ProgressEvent("episode_1.mp4", 400 * 1024, 33 * 1024**2)

    def test_handles_decimals_and_gigabytes(self) -> None:
        event = parse_readout("[#a1 1.5GiB/2.0GiB(75%) CN:8 DL:4.2MiB]", "f")
        assert event == ProgressEvent("f", int(1.5 * 1024**3), 2 * 1024**3)

    def test_an_unknown_size_reads_as_zero_total(self) -> None:
        assert parse_readout("[#a1 0B/0B CN:1 DL:0B]", "f") == ProgressEvent("f", 0, 0)

    def test_older_unit_names_are_read_as_powers_of_1024(self) -> None:
        assert parse_readout("[#a1 1MB/2MB(50%)]", "f") == ProgressEvent("f", 1024**2, 2 * 1024**2)

    def test_other_output_is_ignored(self) -> None:
        assert parse_readout("*** Download Progress Summary ***", "f") is None
        assert parse_readout("", "f") is None


def script(body: str) -> list[str]:
    return [sys.executable, "-c", textwrap.dedent(body)]


class TestRunCaptured:
    def test_progress_lines_become_events(self) -> None:
        command = script(
            r"""
            import sys, time
            for done in (10, 20, 30):
                sys.stdout.write(f"[#a {done}KiB/30KiB({done * 100 // 30}%) CN:1]\r")
                sys.stdout.flush()
            """
        )
        events: list[ProgressEvent] = []
        run_aria2_captured(command, "f", events.append)
        assert [e.done for e in events] == [10 * 1024, 20 * 1024, 30 * 1024]

    def test_a_failing_run_reports_the_exit_code_and_the_last_output(self) -> None:
        command = script("import sys; print('Resource not found'); sys.exit(3)")
        with pytest.raises(DownloadError, match="code 3.*Resource not found"):
            run_aria2_captured(command, "f", lambda _event: None)

    def test_a_missing_program_is_a_download_error(self) -> None:
        with pytest.raises(DownloadError, match="not found"):
            run_aria2_captured(["definitely-not-a-real-program-xyz"], "f", lambda _e: None)

    def test_a_callback_that_raises_stops_the_process(self) -> None:
        command = script(
            r"""
            import sys, time
            sys.stdout.write("[#a 1KiB/9KiB(11%)]\n"); sys.stdout.flush()
            time.sleep(30)
            """
        )

        class Stop(Exception):
            pass

        def stop(_event: ProgressEvent) -> None:
            raise Stop

        started = time.monotonic()
        with pytest.raises(Stop):
            run_aria2_captured(command, "f", stop)
        assert time.monotonic() - started < 10  # it did not wait for the 30 second sleep
