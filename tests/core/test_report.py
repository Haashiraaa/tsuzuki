from tsuzuki.core.report import EpisodeResult, RunReport, SeriesReport


def series(*statuses: str, error: str | None = None) -> SeriesReport:
    report = SeriesReport(url="https://x.example/", error=error)
    report.results = [EpisodeResult(str(i), s) for i, s in enumerate(statuses)]  # type: ignore[arg-type]
    return report


def test_counts_by_status() -> None:
    report = series("completed", "completed", "skipped", "failed")
    assert (report.count("completed"), report.count("skipped"), report.count("failed")) == (2, 1, 1)


def test_a_series_is_ok_only_without_failures_or_errors() -> None:
    assert series("completed", "skipped").ok
    assert not series("completed", "failed").ok
    assert not series("completed", error="page layout changed").ok


def test_exit_code_is_zero_only_when_everything_worked() -> None:
    assert RunReport((series("completed"), series("skipped"))).exit_code == 0
    assert RunReport((series("completed"), series("failed"))).exit_code == 1
    assert RunReport((series(error="boom"),)).exit_code == 1


def test_run_totals_add_up_across_series() -> None:
    run = RunReport((series("completed", "failed"), series("completed", error="boom")))
    assert run.count("completed") == 2
    assert run.failed_series == 1
