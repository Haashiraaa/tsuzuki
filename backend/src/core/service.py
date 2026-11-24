"""The download runner: scrape a series, pick episodes, download them, report what happened.

It knows nothing about the terminal. Everything it learns goes out as events and a report.
"""

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TypeVar

from tsuzuki.core.errors import TsuzukiError
from tsuzuki.core.events import EpisodeEvent, EventHandler, SeriesEvent, ignore_events
from tsuzuki.core.models import DownloadJob, Episode, MediaSource, Selection, Series
from tsuzuki.core.naming import episode_filename, folder_name
from tsuzuki.core.report import EpisodeResult, RunReport, SeriesReport
from tsuzuki.core.retry import RetryNotice, RetryPolicy, retry_call
from tsuzuki.core.selection import select_episodes
from tsuzuki.download.base import Downloader
from tsuzuki.sites.base import Site

T = TypeVar("T")
R = TypeVar("R")
SiteResolver = Callable[[str], Site]


@dataclass(frozen=True)
class RunOptions:
    selection: Selection
    workers: int
    downloads_dir: Path


class DownloadRunner:
    def __init__(
        self,
        *,
        resolve_site: SiteResolver,
        downloader: Downloader,
        options: RunOptions,
        retry: RetryPolicy | None = None,
        emit: EventHandler = ignore_events,
        notify_retry: RetryNotice | None = None,
    ) -> None:
        self._resolve_site = resolve_site
        self._downloader = downloader
        self._options = options
        self._retry = retry or RetryPolicy()
        self._emit = emit
        self._notify_retry = notify_retry

    def run(self, urls: Sequence[str]) -> RunReport:
        """Process every URL; one failing series never stops the others."""
        return RunReport(tuple(self.run_series(url) for url in urls))

    def run_series(self, url: str) -> SeriesReport:
        report = SeriesReport(url=url)
        try:
            self._fill_report(report, url)
        except TsuzukiError as exc:
            report.error = str(exc)
            self._emit(SeriesEvent("failed", url, report.title, detail=str(exc)))
        return report

    def _fill_report(self, report: SeriesReport, url: str) -> None:
        site = self._resolve_site(url)
        series = self._with_retry(lambda: site.fetch_series(url))
        report.title = series.title
        chosen = select_episodes(series.episodes, self._options.selection)
        self._emit(SeriesEvent("found", url, series.title, count=len(chosen)))
        work = partial(self._download_one, site, series)
        report.results = run_in_pool(work, chosen, self._options.workers)

    def _download_one(self, site: Site, series: Series, episode: Episode) -> EpisodeResult:
        """Never raises for expected failures, so one bad episode can't sink the rest."""
        self._emit(EpisodeEvent("started", series.title, episode.number))
        try:
            result = self._fetch_and_download(site, series, episode)
        except (TsuzukiError, OSError) as exc:
            result = EpisodeResult(episode.number, "failed", str(exc))
        self._emit(EpisodeEvent(result.status, series.title, episode.number, result.detail))
        return result

    def _fetch_and_download(self, site: Site, series: Series, episode: Episode) -> EpisodeResult:
        source = self._with_retry(lambda: site.resolve_media(series, episode))
        job = self._build_job(series, episode, source)
        outcome = self._with_retry(lambda: self._downloader.download(job, self._emit))
        status = "skipped" if outcome == "skipped" else "completed"
        return EpisodeResult(episode.number, status)

    def _build_job(self, series: Series, episode: Episode, source: MediaSource) -> DownloadJob:
        directory = self._options.downloads_dir / folder_name(series.title)
        return DownloadJob(source, directory, episode_filename(episode.number))

    def _with_retry(self, func: Callable[[], T]) -> T:
        return retry_call(func, self._retry, on_retry=self._notify_retry)


def run_in_pool(fn: Callable[[T], R], items: Sequence[T], workers: int) -> list[R]:
    """Map ``fn`` over ``items`` with ``workers`` threads (inline when 1)."""
    if workers <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            return list(pool.map(fn, items))
        except KeyboardInterrupt:
            pool.shutdown(wait=False, cancel_futures=True)
            raise
