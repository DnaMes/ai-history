# Contributing to ai-history

## Development Setup

```bash
git clone https://github.com/YOUR-ORG/ai-history.git
cd ai-history
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
mypy ai_history/ --ignore-missing-imports
```

Or run all pre-commit hooks at once:

```bash
pre-commit run --all-files
```

## Adding a New AI Tool Extractor

1. Create `ai_history/extractors/<toolname>.py`
2. Inherit `BaseExtractor` from `ai_history.extractors.base`
3. Implement:
   - `tool` property → return the correct `Tool` enum value
   - `extract_sessions()` → `Iterator[UnifiedSession]`
   - `is_available()` → check if the tool's data directory exists
4. Register in `ai_history/extractors/factory.py`
5. Add the tool to `Tool` enum in `ai_history/core/models.py` if it's new
6. Add a contract test in `tests/test_extractors_contract.py`

See existing extractors (e.g. `claude.py`, `gemini.py`) for patterns. Use `safe_copy_db()` from `BaseExtractor` when reading SQLite files.

## Pull Request Guidelines

- One logical change per PR
- Tests must pass: `python -m pytest tests/`
- Pre-commit hooks must pass
- Follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Do not add cloud dependencies — this project is local-first by design
- Do not hardcode absolute paths; use `Path.home()` / `Path.expanduser()`

## Architecture

See [CLAUDE.md](CLAUDE.md) for a detailed architecture overview.
