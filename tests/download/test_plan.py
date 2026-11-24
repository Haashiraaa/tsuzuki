from tsuzuki.download.hint import aria2_install_hint
from tsuzuki.download.plan import plan_downloads


def test_with_aria2_the_requested_workers_are_used() -> None:
    plan = plan_downloads(4, aria2_present=True)
    assert (plan.workers, plan.hint) == (4, None)


def test_without_aria2_downloads_run_one_at_a_time_with_a_hint() -> None:
    plan = plan_downloads(4, aria2_present=False)
    assert plan.workers == 1
    assert plan.hint and "aria2" in plan.hint


def test_install_hints_per_system() -> None:
    assert "brew" in aria2_install_hint("Darwin")
    assert "apt" in aria2_install_hint("Linux")
    assert "winget" in aria2_install_hint("Windows")
    assert "aria2.github.io" in aria2_install_hint("Plan9")
