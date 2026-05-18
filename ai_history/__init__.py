"""ai-history — local-first AI coding-session history + shared agent memory.

The single source of truth for the package version. ``pyproject.toml``
reads ``__version__`` from here via ``[tool.setuptools.dynamic]``, so the
version is set in exactly one place.

2.3.0: renamed the product to "Lore" (CLI `lore`, data dir ~/.lore with
auto-migration); memory_sources provenance linking. The import package
stays `ai_history`.
"""

__version__ = "2.3.0"
