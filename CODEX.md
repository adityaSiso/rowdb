# RowDB development guide

This file is the editable project guide for Codex-assisted work. Keep its rules
specific to lessons learned in this repository. When a user correction or a
recurring review finding reveals a useful rule, update this file; remove rules
that no longer match the project.

## Project shape

RowDB is a small Python document database. `master.json` tracks the next row ID,
the active partition, and partition ID ranges. Partition data is append-only
NDJSON. Keep changes understandable and scoped to the current task.

## Data integrity and safety

- Row IDs increase monotonically and must never be reused. ID reservations are
  written to `master.json` before partition appends; an append failure may leave
  a gap.
- A database directory supports one open `RowDB` handle at a time. Preserve the
  cross-process lock and release it when the handle closes, including failed
  initialization paths.
- Partition filenames must remain single path components inside the database
  directory. Validate both configured prefixes and names loaded from metadata.
- Replace master metadata atomically. Do not mutate in-memory metadata before a
  successful write.
- Treat repeated row IDs in stored partition data as corruption; never silently
  choose one record over another.

## Local development

- Use the repository's `uv.lock` and `.venv`; do not install project
  dependencies into a global Python environment.
- Supported Python versions are `>=3.10,<3.14`. The checked-in
  `.python-version` selects the default local interpreter.
- Run `uv sync --locked` to create or refresh `.venv` from the lockfile without
  changing dependency resolution.
- Run `uv run pytest --basetemp=.pytest-tmp` for the test suite and
  `uv run ruff check .` for linting.
- Update a feature branch with `git fetch origin` followed by
  `git rebase origin/main`.
- Keep `.venv`, test scratch files, and tool caches out of commits.

## Change workflow

- Add or update a regression test for each bug fix. Prefer tests that exercise
  behavior through `RowDB` and persisted files when practical.
- Preserve Windows and POSIX behavior for file paths and locking.
- Avoid new runtime dependencies unless the change clearly needs them.
- Before committing, inspect `git diff --check`, `git status`, and the complete
  diff. Summarize test results and any limitations in the pull request.
- Update this guide when a new project invariant or development workflow is
  established, not for one-off implementation details.
