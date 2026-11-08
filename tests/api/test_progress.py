from tsuzuki.api.progress import Progress, ProgressBoard


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_unknown_episode_has_no_progress() -> None:
    assert ProgressBoard().get(1) is None


def test_percent_and_eta_from_updates() -> None:
    clock = Clock()
    board = ProgressBoard(clock)
    board.update(1, done=0, total=1000, method="aria2")
    clock.now = 10.0
    board.update(1, done=500, total=1000)
    progress = board.get(1)
    assert progress is not None
    assert progress.method == "aria2"
    assert progress.percent == 50
    assert progress.bytes_per_second == 50
    assert progress.eta_seconds == 10


def test_unknown_total_means_zero_percent_and_no_eta() -> None:
    progress = Progress("stream", bytes_done=500, bytes_total=0, bytes_per_second=10)
    assert progress.percent == 0
    assert progress.eta_seconds is None


def test_percent_never_passes_100() -> None:
    assert Progress("x", 2000, 1000, 1).percent == 100


def test_clear_forgets_progress_and_cancel_request() -> None:
    board = ProgressBoard()
    board.update(1, done=1, total=2)
    board.request_cancel(1)
    assert board.cancel_requested(1)
    board.clear(1)
    assert board.get(1) is None
    assert not board.cancel_requested(1)
