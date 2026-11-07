# Tsuzuki

Tsuzuki (続き, "to be continued") is a personal command-line tool for downloading anime episodes.
Sites are plug-in adapters, so supporting a new one means adding a folder under `src/tsuzuki/sites/`.
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
src/tsuzuki/
    cli/         argument parsing, terminal output, wiring (the only place that prints or exits)
    core/        models, selection, retry, events, report, root folder, and the runner
    sites/       one folder per site + the registry; each site = fetch pages + pure parsing
    download/    aria2c, built-in streaming (resumable), skip-if-complete, and the chooser
    net/         HTTP helpers (timeouts, default headers, error translation), URL helpers
scripts/
    probe_ytdlp.py   check whether yt-dlp can handle a site (run locally)
```

`core/` never prints, parses arguments or exits, so a web front-end can drive the same runner.

## Adding a site

1. Create `src/tsuzuki/sites/<name>/` with a `parsing.py` (pure HTML-to-data functions) and a
   `site.py` with a class implementing `Site` (`fetch_series`, `resolve_media`) and an `ENTRY`.
2. Add the `ENTRY` to the list in `sites/registry.py`.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && pyright
```

Commit messages use [Conventional Commits](https://www.conventionalcommits.org/)
(`feat: ...`, `fix: ...`): the changelog, version bumps and releases are generated from them.
See [docs/releasing.md](docs/releasing.md).
