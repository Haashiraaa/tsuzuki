"""What happened during a run. The CLI prints it; a web UI could render it."""

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["completed", "skipped", "failed"]


@dataclass(frozen=True)
class EpisodeResult:
    episode: str
    status: Status
    detail: str = ""


@dataclass
class SeriesReport:
    url: str
    title: str = ""
    results: list[EpisodeResult] = field(default_factory=list[EpisodeResult])
    error: str | None = None

    def count(self, status: Status) -> int:
        return sum(1 for result in self.results if result.status == status)

    @property
    def ok(self) -> bool:
        return self.error is None and self.count("failed") == 0


@dataclass(frozen=True)
class RunReport:
    series: tuple[SeriesReport, ...]

    def count(self, status: Status) -> int:
        return sum(item.count(status) for item in self.series)

    @property
    def failed_series(self) -> int:
        return sum(1 for item in self.series if item.error is not None)

    @property
    def exit_code(self) -> int:
        return 0 if all(item.ok for item in self.series) else 1
