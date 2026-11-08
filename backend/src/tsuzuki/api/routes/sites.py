"""The Sites screen."""

from fastapi import APIRouter, HTTPException, Response

from tsuzuki.api.deps import State
from tsuzuki.api.ladder import steps_for_url
from tsuzuki.api.schemas import SiteOut, SiteTestOut, SiteUrlIn
from tsuzuki.sites.registry import known_sites

router = APIRouter()


@router.get("/sites")
def list_sites() -> list[SiteOut]:
    return [
        SiteOut(host=host, how="Built-in adapter", state="working")
        for entry in known_sites()
        for host in entry.hosts
    ]


@router.post("/sites/test")
def test_site(body: SiteUrlIn, state: State) -> SiteTestOut:
    """Says what Tsuzuki can do with this site. Only built-in adapters can be reported on for
    now; trying an unknown site needs the generic detection and yt-dlp steps."""
    host, steps = steps_for_url(body.url)
    return SiteTestOut(host=host, steps=steps, profile_path=None)


@router.post("/sites/profiles")
def save_profile(_body: SiteUrlIn) -> Response:
    raise HTTPException(501, "Saving site profiles is not supported yet.")
