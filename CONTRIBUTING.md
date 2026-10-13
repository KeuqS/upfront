# Contributing

Thanks for helping. Bug reports with a config that reproduces the problem are the most useful
contribution: say which agent, which config file, and paste the relevant `upfront --json` output.

## Setup

You need [uv](https://docs.astral.sh/uv/). Python 3.11+ is installed by uv if missing.

```bash
git clone https://github.com/thanatchon36/upfront && cd upfront
uv sync
uv run pre-commit install
```

## Checks (the same ones CI runs)

```bash
uv run pre-commit run --all-files     # ruff check, ruff format, mypy --strict
uv run pytest --cov --cov-fail-under=85
```

Tests start real MCP servers from `examples/servers/replay_server.py`, so they need no network
except the tokenizer download on first run.

## Adding a compatibility rule

Rules live in `src/upfront/compat.py`. Every rule must link the public issue or documentation
it comes from and needs a test with a tool that triggers it and one that doesn't. Rules that
can't cite a source won't be merged: a false "this breaks in X" is worse than no warning.

## Adding a harness

Add a reader in `src/upfront/discover.py`, a fixture config under `tests/fixtures/`, and link
the harness's documentation for the config format in the reader's docstring.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- One logical change per pull request, with tests. Add a line under `[Unreleased]` in CHANGELOG.md.
