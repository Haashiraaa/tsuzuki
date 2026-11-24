from datetime import timedelta
from pathlib import Path

from tsuzuki.api.__main__ import build_parser, state_from


def test_defaults_listen_on_this_computer_only() -> None:
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_settings_reach_the_state(tmp_path: Path) -> None:
    args = build_parser().parse_args(
        ["-o", str(tmp_path), "--slots", "2", "--keep-hours", "6", "--max-waiting-gb", "1.5"]
    )
    state = state_from(args)
    assert state.root.path == tmp_path.resolve()
    assert state.slots == 2
    assert state.retention.ttl == timedelta(hours=6)
    assert state.retention.max_ready_bytes == int(1.5 * 1024**3)


def test_no_size_cap_by_default(tmp_path: Path) -> None:
    state = state_from(build_parser().parse_args(["-o", str(tmp_path)]))
    assert state.retention.max_ready_bytes is None
