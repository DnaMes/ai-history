# Contributing to Lore

> The product/CLI is **Lore** (`lore`), but the Python import package is
> `lore` — the import name was deliberately not renamed. Paths like
> `lore/...` below refer to the code package, not the product name.

## Development Setup

```bash
git clone https://github.com/DnaMes/lore.git
cd lore
python -m venv .venv && source .venv/bin/activate
pip install -e .
pre-commit install
```

## Running Tests

```bash
# All tests
python -m pytest tests/

# Single file
python -m pytest tests/test_extractors_contract.py

# Pattern match
python -m pytest tests/ -k "opencode"

# With output
python -m pytest tests/ -v --tb=short
```

## Lint & Format

```bash
black . --line-length=100
isort . --profile black --line-length=100
flake8 . --max-line-length=100 --ignore=E501,W503,E203
mypy lore/ --ignore-missing-imports
```

Or run all pre-commit hooks at once:

```bash
pre-commit run --all-files
```

## Adding a New AI Tool Extractor

1. Create `lore/extractors/<toolname>.py`
2. Inherit `BaseExtractor` from `lore.extractors.base`
3. Implement:
   - `tool` property → return the correct `Tool` enum value
   - `extract_sessions()` → `Iterator[UnifiedSession]`
   - `is_available()` → check if the tool's data directory exists
4. Register in `lore/extractors/factory.py`
5. Add the tool to `Tool` enum in `lore/core/models.py` if it's new
6. Add a contract test in `tests/test_extractors_contract.py`

See existing extractors (e.g. `claude.py`, `gemini.py`) for patterns. Use `safe_copy_db()` from `BaseExtractor` when reading SQLite files.

## Pull Request Guidelines

- One logical change per PR
- Tests must pass: `python -m pytest tests/`
- Pre-commit hooks must pass
- Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Do not add cloud dependencies — this project is local-first by design
- Do not hardcode absolute paths; use `Path.home()` / `Path.expanduser()`

## Releasing

The version is defined in exactly one place: `__version__` in
`lore/__init__.py` (`pyproject.toml` reads it dynamically). To cut a
release:

1. Bump `__version__` in `lore/__init__.py` (semantic versioning).
2. Move the `[Unreleased]` entries in `CHANGELOG.md` into a new dated
   `[X.Y.Z]` section.
3. Commit: `docs: changelog for X.Y.Z` together with the version bump.
4. Tag the commit: `git tag -a vX.Y.Z -m "Lore X.Y.Z — <summary>"`.
5. Push the branch and the tag: `git push <remote> main vX.Y.Z`.
6. Optionally build + publish the wheel: `python -m build`.

The web UI (sidebar footer), `lore --version`, and
`/api/build-info` all surface the version automatically.

## Architecture

See [CLAUDE.md](CLAUDE.md) for a detailed architecture overview.
