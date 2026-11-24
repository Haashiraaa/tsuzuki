"""``python -m tsuzuki.api``: start the server."""

import argparse
import sys
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

from tsuzuki.api.app import create_app
from tsuzuki.api.state import DEFAULT_SLOTS, ApiState, Limits
from tsuzuki.core.root import resolve_root
from tsuzuki.storage import RetentionPolicy

LOOPBACK = ("127.0.0.1", "localhost", "::1")
GIB = 1024**3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tsuzuki.api", description="Run the Tsuzuki server."
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="address to listen on (default: this computer only)"
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "-o", "--output", type=Path, help="root folder for Downloads/ and the database"
    )
    parser.add_argument("--slots", type=int, default=DEFAULT_SLOTS, help="downloads at once")
    parser.add_argument(
        "--max-open",
        type=int,
        default=Limits.max_open,
        help="episodes one visitor can have waiting",
    )
    parser.add_argument(
        "--max-series", type=int, default=Limits.max_series, help="series in one visitor's library"
    )
    parser.add_argument(
        "--keep-hours", type=float, default=24, help="hours a finished file waits on the server"
    )
    parser.add_argument(
        "--max-waiting-gb",
        type=float,
        help="stop starting downloads when finished files reach this size",
    )
    return parser


def state_from(args: argparse.Namespace) -> ApiState:
    cap = None if args.max_waiting_gb is None else int(args.max_waiting_gb * GIB)
    retention = RetentionPolicy(ttl=timedelta(hours=args.keep_hours), max_ready_bytes=cap)
    limits = Limits(max_open=args.max_open, max_series=args.max_series)
    return ApiState(
        root=resolve_root(args.output), retention=retention, slots=args.slots, limits=limits
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print("The server needs extra packages: pip install 'tsuzuki[server]'", file=sys.stderr)
        return 1
    if args.host not in LOOPBACK:
        print(
            "Warning: this server has no login. Anyone who can reach it can queue downloads and "
            "take files. Put it behind a reverse proxy with a password, or a private network.",
            file=sys.stderr,
        )
    uvicorn.run(create_app(state_from(args)), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
