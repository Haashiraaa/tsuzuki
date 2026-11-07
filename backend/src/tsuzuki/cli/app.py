"""CLI wiring: parse arguments, build the pieces, run, translate the result to an exit code."""

import argparse
import logging
from collections.abc import Sequence

from haashi.utility import JsonlErrorLogger, Logger

from tsuzuki.cli.args import parse_args, retry_from, selection_from
from tsuzuki.cli.output import ConsoleReporter, print_summary
from tsuzuki.core.errors import TsuzukiError
from tsuzuki.core.root import Root, resolve_root
from tsuzuki.core.service import DownloadRunner, RunOptions
from tsuzuki.download.plan import DownloadPlan, plan_downloads
from tsuzuki.sites.registry import site_for

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPTED = 130
ERROR_LOG_MAX_BYTES = 1_000_000
ERROR_LOG_BACKUPS = 3


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns the process exit code."""
    args = parse_args(argv)
    root = resolve_root(args.output)
    logger = build_logger(args.debug, root)
    try:
        return run(args, root, logger)
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return EXIT_INTERRUPTED
    except TsuzukiError as exc:
        logger.error(str(exc))
        return EXIT_FAILURE
    except Exception as exc:  # last-resort boundary: log with traceback, exit cleanly
        logger.error(f"Unexpected error: {exc}", exception=exc, save_to_json=True, context="cli")
        return EXIT_FAILURE


def build_logger(debug: bool, root: Root) -> Logger:
    """Console logger; unexpected errors are also saved as JSON lines under ``<root>/logs``."""
    error_log = JsonlErrorLogger(
        log_dir=root.logs, max_bytes=ERROR_LOG_MAX_BYTES, backups=ERROR_LOG_BACKUPS
    )
    return Logger(logging.DEBUG if debug else logging.INFO, error_logger=error_log)


def run(args: argparse.Namespace, root: Root, logger: Logger) -> int:
    logger.debug(f"Root folder: {root.path} (from {root.source})")
    plan = plan_downloads(args.workers, notice=logger.warning)
    announce_plan(plan, logger)
    reporter = ConsoleReporter(logger)
    runner = build_runner(args, root, plan, reporter)
    try:
        report = runner.run(args.urls)
    finally:
        reporter.close()
    print_summary(report, logger)
    return report.exit_code


def announce_plan(plan: DownloadPlan, logger: Logger) -> None:
    if plan.hint:
        logger.warning("aria2c not found: downloads will be sequential and slower.")
        logger.warning(f"For faster parallel downloads, install it: {plan.hint}")


def build_runner(
    args: argparse.Namespace, root: Root, plan: DownloadPlan, reporter: ConsoleReporter
) -> DownloadRunner:
    options = RunOptions(
        selection=selection_from(args), workers=plan.workers, downloads_dir=root.downloads
    )
    return DownloadRunner(
        resolve_site=site_for,
        downloader=plan.downloader,
        options=options,
        retry=retry_from(args),
        emit=reporter.handle,
        notify_retry=reporter.retry_notice,
    )
