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

Downloads run in the background while the server is up: `--slots` of them at once (default 3),
oldest request first, using aria2c when it is installed and the built-in downloader otherwise.
If the server stops, running downloads go back in the queue and carry on from where they stopped.
`--max-waiting-gb` pauses the queue while finished-but-uncollected files fill that much disk.

**Every browser gets its own library and queue, with no accounts.** The first time someone adds
a series, the server gives their browser a random cookie (`tsuzuki_visitor`, kept a year; only
a hash of it is stored). Series, episodes and downloaded files are shared, so if two people ask
for the same episode it is downloaded once; what each person sees (library, counts, queue,
"saved") is theirs. A file is deleted when the last person who asked for it has saved it.
**Settings > Your library link** is a private link that brings a library back on another device
or after clearing cookies. Anyone holding it can use that library.

Fairness and limits, per visitor (change with `--max-open` and `--max-series`):

- `--max-open` (default 12): episodes queued, downloading or waiting to be saved at once.
  A batch that would go over is refused whole (HTTP 429).
- `--max-series` (default 60) series in a library.
- The queue is fair, not first come first served: the next download goes to whoever has the
  fewest running, then by place in their own list, so one person queueing 12 episodes cannot
  make everyone else wait behind them.
- Adding a series that was read from its site in the last hour reuses it instead of asking
  the site again.

There is no per-IP rate limiting in the app; use Caddy's rate limiting if you need it. For a big
disk (say 2-3 TB) raise `--max-waiting-gb` so the queue pauses only when uncollected files
really fill it.

Not built yet: pausing, and saving site profiles (those routes answer "not supported yet").

## Storage

One SQLite file, `<root>/tsuzuki.db`, read and written with Python's built-in `sqlite3` (no ORM).
Its schema is managed by **Alembic**: migrations are hand-written files in
`backend/src/tsuzuki/storage/migrations/versions/`, and the database upgrades itself when the
server starts. To change the schema, from the repository root:

```bash
alembic revision --rev-id 0002 -m "what changes"    # then fill in upgrade() in the new file
```

Never edit a migration that has been released; add a new one. Each migration runs in its own
transaction, so a failure leaves the database at the last good version.

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
