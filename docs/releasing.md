# Releasing

Changelog, version numbers and tags are automated. You never edit `CHANGELOG.md`, bump the
version or run `git tag` by hand. What drives it all is the **commit message**.

> Status: this setup was written and checked locally (workflow syntax, the wheel build and
> smoke test, the commit checker), but it has not run on GitHub yet. The first release is the
> real test. Expect to adjust `release-please-config.json` once.

## How it works

Releases happen **only from `main`**.

1. Work is merged into `main` with commit messages in
   [Conventional Commits](https://www.conventionalcommits.org/) form (`feat: ...`, `fix: ...`).
2. On every push to `main`, the **Release** workflow (`.github/workflows/release.yml`) runs
   [release-please](https://github.com/googleapis/release-please). It reads the commits since
   the last release and keeps one pull request open, titled `chore(main): release X.Y.Z`.
3. That pull request contains only the new `CHANGELOG.md` section and the version bump
   (`pyproject.toml` and `.release-please-manifest.json`).
4. **A person merges that pull request when they want to ship.** Merging creates the tag
   `vX.Y.Z` and a GitHub Release with the same notes, and the workflow then builds the wheel
   and sdist and attaches them to that release. Until then nothing is tagged.

## What each commit type does

| Commit type | Appears in changelog | Version effect (before 1.0) |
|---|---|---|
| `feat:` | Features | minor bump (0.2.1 → 0.3.0) |
| `fix:` | Bug fixes | patch bump (0.2.1 → 0.2.2) |
| `perf:` | Performance | patch bump |
| `refactor:`, `docs:` | Refactoring, Documentation | no release on their own |
| `test:`, `chore:`, `ci:`, `build:`, `style:` | hidden | no release on their own |
| `feat!:` or a `BREAKING CHANGE:` footer | Features, flagged | minor bump before 1.0, major after |

Before 1.0.0, breaking changes bump the *minor* number. To go to 1.0.0 deliberately, put
`Release-As: 1.0.0` as a footer line of any commit on `main`.

The CI job **Commit messages (advisory)** warns about subjects that are not in this form. It
never fails the build; a message in the wrong form is simply left out of the changelog.

## One-time setup (do these in GitHub, not in code)

1. **Allow Actions to open pull requests:** repository Settings → Actions → General →
   Workflow permissions → tick "Allow GitHub Actions to create and approve pull requests".
2. **Create the token `RELEASE_PLEASE_TOKEN`:** a personal access token (fine-grained, this
   repository only) with *Contents: read and write* and *Pull requests: read and write*. Save it
   as a repository secret with that exact name. Why: pull requests opened by the default token
   do not trigger CI, so the required `ci-ok` check would never run on the release pull request
   and you could not merge it. Without the secret the workflow still runs, but you would have to
   merge the release pull request by bypassing the check.
3. **Protect `main`** (below).

## First release

`release-please-config.json` has a `bootstrap-sha`: the commit from which history is counted
(the head of `main` before the restructure). Commits before it are ignored. The manifest says
the current version is `0.2.1`, which matches the existing `v0.2.1` tag.

The restructure into Tsuzuki changes the command name (`anime` → `tsuzuki`) and the Python
package, so it is a breaking change. **Squash-merge it with one conventional title**, for
example:

```
feat!: rename to tsuzuki and restructure into feature packages
```

release-please will then propose `0.3.0` (breaking changes bump the minor number before 1.0).
Commits that are not in conventional form are ignored rather than failing anything. Do not
rewrite already-pushed history to fix a message.

## Protecting `main`

- Settings → Rules → Rulesets (or Branches → branch protection) → target `main`.
- Require a pull request before merging.
- Require the status check **`ci-ok`**. It is green only when lint, types, the whole test matrix
  and the wheel build are green. (The matrix job names change between the full and the reduced
  version, which is why `ci-ok` exists.)
- Block force pushes and deletion.

On GitHub Free, private repositories may not offer enforced rules. If the options are greyed
out, make the repository public or rely on only ever installing tagged releases.

## What CI runs

| Job | What it checks |
|---|---|
| Lint, format, types | `ruff check`, `ruff format --check`, `pyright` (strict on `src`) |
| Test | the command starts on every OS and Python in the matrix; `pytest` runs automatically once a `tests/` folder with `test_*.py` files exists |
| Build and smoke-test the wheel | `python -m build`, `twine check --strict`, then install the wheel in a clean venv outside the repo and run `tsuzuki` |
| Commit messages (advisory) | warns about subjects the changelog would skip |
| ci-ok | the single required check |

Full matrix (Ubuntu, macOS, Windows × Python 3.10-3.14) runs on `main` and on pull requests into
`main`; other branches run Ubuntu and Windows on 3.10 and 3.14.

## If something goes wrong

- **The release pull request has a wrong version:** add a `Release-As: X.Y.Z` footer commit on
  `main`, or edit the pull request's branch; release-please recomputes on the next push.
- **A release was tagged by mistake:** delete the GitHub Release and the tag, then fix the
  version in `.release-please-manifest.json` by hand in a normal pull request.
- **The Release workflow fails with a permissions error:** setup step 1 or 2 was missed.
- **The changelog is missing a change:** its commit message was not in conventional form, or it
  is a hidden type (`chore`, `test`, ...).
- **A pull request was squash-merged with a non-conventional title, so no release appeared:**
  edit the *merged* pull request's description and add the block below, then push anything to
  `main` so release-please runs again and reads it:

  ```
  BEGIN_COMMIT_OVERRIDE
  feat: add a second site adapter
  END_COMMIT_OVERRIDE
  ```
