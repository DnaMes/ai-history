"""ai-history — local-first AI coding-session history + shared agent memory.

The single source of truth for the package version. ``pyproject.toml``
reads ``__version__`` from here via ``[tool.setuptools.dynamic]``, so the
version is set in exactly one place.

Bumped to 2.1.0: v2 SQLite store, cross-tool agent memory, semantic
recall, and the /memory web page.
"""

__version__ = "2.1.0"
