# Tsuzuki

Tsuzuki (続き, "to be continued") is a personal command-line tool for downloading anime episodes.
Sites are plug-in adapters, so supporting a new one means adding a folder under `backend/src/tsuzuki/sites/`.
Currently supported: AnimeHeaven.

## Install

```bash
git clone https://github.com/Haashiraaa/tsuzuki
cd tsuzuki
pip install -e .
```

Dependencies are declared in `pyproject.toml` only. aria2c is optional but recommended
(parallel, multi-connection downloads); a per-OS install hint is printed if it's missing.

## Usage

```bash
tsuzuki --urls "https://animeheaven.me/anime.php?9rp26"
python -m tsuzuki --urls "..."      # same thing
```

| Flag | Meaning |
|------|---------|
| `--urls URL [URL ...]` | series page URLs (required) |
| `--episode N` | download one episode by number |
| `--limit N` | download only N episodes (newest by default) |
| `--oldest` | with `--limit`: take the oldest instead |
| `--workers N` | parallel downloads when aria2c is installed (default 3) |
| `--retries N` | attempts per network step (default 5) |
| `-o, --output DIR` | root folder for `Downloads/` and `logs/` |
| `-d, --debug` | verbose logging |

`--episode` and `--limit` can't be combined. Exit code is 0 when everything succeeded,
1 if anything failed, 130 if interrupted.

## Where files go

The root folder is chosen in this order, and the first that applies wins:

1. `--output DIR`
2. the `TSUZUKI_HOME` environment variable
3. the project folder (found by name with haashi's `get_ancestor_by_name`, so it works from a git clone)
4. `~/tsuzuki`

Downloads go to `<root>/Downloads/<series>/episode_<n>.mp4`; unexpected errors are logged as
JSON lines to `<root>/logs/errors_log.jsonl`. Run with `-d` to see which root was picked.

## Layout

```
backend/src/tsuzuki/
    cli/         argument parsing, terminal output, wiring (the only place that prints or exits)
    core/        models, selection, retry, events, report, root folder, and the runner
    sites/       one folder per site + the registry; each site = fetch pages + pure parsing
    download/    aria2c, built-in streaming (resumable), skip-if-complete, and the chooser
    net/         HTTP helpers (timeouts, default headers, error translation), URL helpers
    storage/     SQLite: series, episodes and what became of each download (see below)
    api/         the web API the frontend talks to (see below)
tests/           mirrors backend/src/tsuzuki: tests/storage tests tsuzuki.storage, and so on
scripts/
    probe_ytdlp.py   check whether yt-dlp can handle a site (run locally)
```

`core/` never prints, parses arguments or exits, so a web front-end can drive the same runner.

## Web server

```bash
pip install -e ".[server]"
python -m tsuzuki.api              # http://127.0.0.1:8000, interactive docs at /api/docs
python -m tsuzuki.api --help       # port, folder, slots, how long finished files wait
```

The routes are the ones listed in `frontend/README.md`. Saving an episode to a device
(`GET /api/episodes/<id>/file`) deletes the server's copy once the last byte has been sent;
an episode nobody collects is removed after 24 hours (`--keep-hours`). Its row stays, so the
library still shows it as downloaded, and asking for it again fetches it from the site.

**There is no login yet.** By default the server only listens on this computer. Before putting
it on a public server, put it behind a reverse proxy that asks for a password (or a private
network such as Tailscale).

Not built yet: the background worker that actually runs queued downloads, pausing, and saving
site profiles (those routes answer "not supported yet").

## Storage

One SQLite file, `<root>/tsuzuki.db`, using only Python's built-in `sqlite3` (no ORM, no Alembic).
The schema is versioned with SQLite's own `user_version` and numbered files in
`backend/src/tsuzuki/storage/migrations/`; add a new `NNNN_name.sql` to change it and never edit
one that has been released.

An episode moves through `available -> queued -> downloading -> ready -> delivered`
(or `expired`, or `failed`; the last three can be queued again). The server keeps a finished file
only until it reaches a device or its time runs out, then deletes the file and keeps the row, so a
download stays on record without filling the disk. See `storage/lifecycle.py`.

## Adding a site

1. Create `backend/src/tsuzuki/sites/<name>/` with a `parsing.py` (pure HTML-to-data functions) and a
   `site.py` with a class implementing `Site` (`fetch_series`, `resolve_media`) and an `ENTRY`.
2. Add the `ENTRY` to the list in `sites/registry.py`.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && pyright
pytest
```

Commit messages use [Conventional Commits](https://www.conventionalcommits.org/)
(`feat: ...`, `fix: ...`): the changelog, version bumps and releases are generated from them.
See [docs/releasing.md](docs/releasing.md).
