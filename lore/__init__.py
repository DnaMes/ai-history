"""Lore — local-first AI coding-session history + shared agent memory.

The single source of truth for the package version. ``pyproject.toml``
reads ``__version__`` from here via ``[tool.setuptools.dynamic]``, so the
version is set in exactly one place.

2.4.0: completed the rename — the Python import package is now ``lore``
(was ``ai_history``); CLI entry modules are ``lore_cli`` / ``lore_session_cli``;
environment variables are ``LORE_*`` (old ``AI_HISTORY_*`` names still read
as deprecated aliases via :func:`_alias_legacy_env`). Data dir stays
``~/.lore`` with auto-migration from the legacy ``~/.ai-history``.
"""

import os

__version__ = "2.4.0"

# Literal legacy prefix — kept verbatim on purpose so existing AI_HISTORY_*
# configs keep working. Do NOT bulk-rename this string to LORE_.
_LEGACY_ENV_PREFIX = "AI_HISTORY_"  # split so a blind sed can't rewrite it
_NEW_ENV_PREFIX = "LORE_"


def _alias_legacy_env() -> None:
    """Back-compat: map any set ``AI_HISTORY_*`` env var onto ``LORE_*``.

    The package was renamed from ``ai_history`` to ``lore``; its config env
    vars moved to the ``LORE_*`` prefix. Existing setups (systemd units,
    docker-compose, shells) may still export the old names, so on import we
    copy each legacy value to the new name *unless* the new name is already
    set (new wins). Runs once at import; never overwrites an explicit
    ``LORE_*`` value.
    """
    for key, value in list(os.environ.items()):
        if not key.startswith(_LEGACY_ENV_PREFIX):
            continue
        new_key = _NEW_ENV_PREFIX + key[len(_LEGACY_ENV_PREFIX) :]
        os.environ.setdefault(new_key, value)


_alias_legacy_env()
