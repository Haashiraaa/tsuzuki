"""The "how Tsuzuki reads a site" steps shown on the series and sites screens.

Only the built-in adapters exist so far. The other rungs (saved profiles, generic detection,
yt-dlp, AI repair) are reported honestly as not built yet.
"""

from tsuzuki.api.schemas import StepOut
from tsuzuki.net.urls import hostname
from tsuzuki.sites.registry import known_sites

NOT_BUILT = "Not built yet."


def built_in_steps(site_name: str) -> list[StepOut]:
    """A site that has its own adapter: the first rung covers it and the rest are not needed."""
    return [
        StepOut(
            title="Saved profile",
            outcome="worked",
            summary="Used",
            detail=f"Built-in {site_name} adapter.",
        ),
        *skipped_rungs("Not needed, the built-in adapter handled it."),
    ]


def unknown_site_steps() -> list[StepOut]:
    return [
        StepOut(
            title="Saved profile",
            outcome="missing",
            summary="None yet",
            detail="This site has not been seen before.",
        ),
        StepOut(
            title="Generic detection",
            outcome="missing",
            summary="Not available yet",
            detail=NOT_BUILT,
        ),
        StepOut(title="yt-dlp", outcome="missing", summary="Not available yet", detail=NOT_BUILT),
        StepOut(
            title="AI repair", outcome="skipped", summary="Not available yet", detail=NOT_BUILT
        ),
    ]


def skipped_rungs(detail: str) -> list[StepOut]:
    return [
        StepOut(title=title, outcome="skipped", summary="Skipped", detail=detail)
        for title in ("Generic detection", "yt-dlp", "AI repair")
    ]


def steps_for_url(url: str) -> tuple[str, list[StepOut]]:
    """The host and the steps for a URL someone wants to try."""
    host = hostname(url)
    for entry in known_sites():
        if any(host == known or host.endswith(f".{known}") for known in entry.hosts):
            return host, built_in_steps(entry.name)
    return host, unknown_site_steps()
