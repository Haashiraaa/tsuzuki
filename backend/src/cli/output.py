"""Terminal output: logging of events, progress bars and the final summary."""

from __future__ import annotations

import threading
from typing import Any

from haashi.utility import Logger
from tqdm import tqdm

from tsuzuki.core.events import EpisodeEvent, Event, ProgressEvent, SeriesEvent
from tsuzuki.core.report import RunReport


class ProgressBars:
    """One tqdm bar per file being written. Safe to call from worker threads."""

    def __init__(self) -> None:
        self._bars: dict[str, tqdm[Any]] = {}
        self._lock = threading.Lock()

    def update(self, event: ProgressEvent) -> None:
        with self._lock:
            bar = self._bars.get(event.filename) or self._open(event)
            bar.n = event.done
            bar.refresh()
            if event.total and event.done >= event.total:
                self._close(event.filename)

    def close_all(self) -> None:
        with self._lock:
            for name in list(self._bars):
                self._close(name)

    def _open(self, event: ProgressEvent) -> tqdm[Any]:
        bar: tqdm[Any] = tqdm(
            total=event.total or None,
            initial=event.done,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=event.filename,
        )
        self._bars[event.filename] = bar
        return bar

    def _close(self, name: str) -> None:
        self._bars.pop(name).close()


class ConsoleReporter:
    """Turns runner events into log lines and progress bars."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._bars = ProgressBars()

    def handle(self, event: Event) -> None:
        if isinstance(event, ProgressEvent):
            self._bars.update(event)
        elif isinstance(event, SeriesEvent):
            self._log_series(event)
        else:
            self._log_episode(event)

    def retry_notice(self, attempt: int, attempts: int, exc: BaseException, delay: float) -> None:
        self._logger.warning(
            f"Attempt {attempt}/{attempts} failed: {exc}. Retrying in {delay:.0f}s"
        )

    def close(self) -> None:
        self._bars.close_all()

    def _log_series(self, event: SeriesEvent) -> None:
        if event.kind == "found":
            self._logger.info(f"{event.title}: {event.count} episode(s) selected")
        else:
            self._logger.error(f"{event.url}: {event.detail}")

    def _log_episode(self, event: EpisodeEvent) -> None:
        label = f"Episode {event.episode}"
        if event.kind == "started":
            self._logger.info(f"{label}: starting")
        elif event.kind == "skipped":
            self._logger.info(f"{label}: already downloaded, skipping")
        elif event.kind == "completed":
            self._logger.info(f"{label}: done")
        else:
            self._logger.error(f"{label}: failed - {event.detail}")


def summary_line(report: RunReport) -> str:
    parts = [
        f"{report.count('completed')} downloaded",
        f"{report.count('skipped')} skipped",
        f"{report.count('failed')} failed",
    ]
    if report.failed_series:
        parts.append(f"{report.failed_series} series failed")
    return ", ".join(parts)


def print_summary(report: RunReport, logger: Logger) -> None:
    logger.info(f"Finished: {summary_line(report)}")
