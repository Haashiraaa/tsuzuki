"""Command-line arguments."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from tsuzuki import __version__
from tsuzuki.core.models import Selection
from tsuzuki.core.retry import RetryPolicy

DEFAULT_WORKERS = 3
DEFAULT_RETRIES = 5


def positive_int(value: str) -> int:
    """argparse type: an integer of 1 or more."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or greater")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsuzuki", description="Download anime episodes.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    add_source_options(parser)
    add_selection_options(parser)
    add_behaviour_options(parser)
    return parser


def add_source_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--urls", nargs="+", required=True, metavar="URL", help="series page URLs")
    parser.add_argument(
        "-o", "--output", type=Path, help="root folder for Downloads/ and logs/ (default: auto)"
    )


def add_selection_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--episode", type=positive_int, help="download one episode by number")
    group.add_argument("--limit", type=positive_int, help="download only N episodes")
    parser.add_argument(
        "--oldest", action="store_true", help="with --limit: take the oldest (default: newest)"
    )


def add_behaviour_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workers",
        type=positive_int,
        default=DEFAULT_WORKERS,
        help=f"parallel downloads when aria2c is installed (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--retries",
        type=positive_int,
        default=DEFAULT_RETRIES,
        help=f"attempts per network step (default: {DEFAULT_RETRIES})",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="verbose logging")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def selection_from(args: argparse.Namespace) -> Selection:
    return Selection(episode=args.episode, limit=args.limit, newest_first=not args.oldest)


def retry_from(args: argparse.Namespace) -> RetryPolicy:
    return RetryPolicy(attempts=args.retries)
