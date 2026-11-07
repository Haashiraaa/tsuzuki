"""Find the adapter for a URL."""

from tsuzuki.core.errors import SiteNotSupportedError
from tsuzuki.net.urls import hostname
from tsuzuki.sites import animeheaven
from tsuzuki.sites.base import Site, SiteEntry

_ENTRIES: list[SiteEntry] = [animeheaven.ENTRY]


def register(entry: SiteEntry) -> None:
    """Add a site at runtime (used by tests and local experiments)."""
    _ENTRIES.append(entry)


def site_for(url: str) -> Site:
    """Adapter for ``url``'s host. Raises ``SiteNotSupportedError`` listing what is supported."""
    host = hostname(url)
    for entry in _ENTRIES:
        if host_matches(host, entry.hosts):
            return entry.create()
    raise SiteNotSupportedError(
        f"No site adapter for {host!r}. Supported: {', '.join(supported_hosts())}"
    )


def host_matches(host: str, hosts: tuple[str, ...]) -> bool:
    """Exact match or a subdomain of a known host."""
    return any(host == known or host.endswith(f".{known}") for known in hosts)


def supported_hosts() -> list[str]:
    return [host for entry in _ENTRIES for host in entry.hosts]
