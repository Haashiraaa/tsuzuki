"""Check whether yt-dlp can extract video from the anime pages you give it.

Run this on your own machine (it needs internet access and ``pip install yt-dlp``):

    python scripts/probe_ytdlp.py URL [URL ...]

For each URL it prints what yt-dlp found (title, number of formats, which extractor
handled it) or why it failed. Nothing is downloaded.
"""

import sys
from collections.abc import Sequence
from typing import Any

OPTIONS: dict[str, Any] = {"quiet": True, "no_warnings": True, "skip_download": True}


def probe(url: str) -> str:
    """One-line verdict for ``url``."""
    from yt_dlp import YoutubeDL  # imported late so --help style errors are friendly

    try:
        with YoutubeDL(OPTIONS) as ydl:  # type: ignore[arg-type]
            info: Any = ydl.extract_info(url, download=False)
    except Exception as exc:  # yt-dlp raises many error types; any of them means "no"
        return f"FAIL  {type(exc).__name__}: {str(exc)[:120]}"
    return describe(info)


def describe(info: Any) -> str:
    extractor = info.get("extractor_key", "?")
    title = info.get("title", "?")
    formats = len(info.get("formats") or [])
    entries = len(info.get("entries") or [])
    return f"OK    extractor={extractor} title={title!r} formats={formats} entries={entries}"


def main(urls: Sequence[str]) -> int:
    if not urls:
        print(__doc__)
        return 2
    for url in urls:
        print(f"{url}\n  {probe(url)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
