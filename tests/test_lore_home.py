"""Tests for the ~/.ai-history → ~/.lore rename + auto-migration."""

from __future__ import annotations

import ai_history.utils.paths as paths


def _reset():
    """Clear the one-shot migration flag so each test runs the logic fresh."""
    paths._migration_done = False


def test_lore_home_returns_dot_lore(tmp_path, monkeypatch):
    _reset()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    home = paths.lore_home()
    assert home == tmp_path / ".lore"


def test_migrates_legacy_dir(tmp_path, monkeypatch):
    """An existing ~/.ai-history is renamed to ~/.lore on first call."""
    _reset()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    legacy = tmp_path / ".ai-history"
    legacy.mkdir()
    (legacy / "index.json").write_text("{}", encoding="utf-8")

    home = paths.lore_home()

    assert home == tmp_path / ".lore"
    assert (tmp_path / ".lore" / "index.json").exists()
    assert not legacy.exists()


def test_no_migration_when_new_dir_exists(tmp_path, monkeypatch):
    """If ~/.lore already exists, the legacy dir is left untouched."""
    _reset()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    new = tmp_path / ".lore"
    new.mkdir()
    (new / "current.json").write_text("new", encoding="utf-8")
    legacy = tmp_path / ".ai-history"
    legacy.mkdir()
    (legacy / "old.json").write_text("old", encoding="utf-8")

    home = paths.lore_home()

    assert home == new
    # Both dirs survive — no clobbering.
    assert (new / "current.json").exists()
    assert legacy.exists()


def test_no_legacy_dir_just_returns_path(tmp_path, monkeypatch):
    """Fresh install — no legacy dir, no ~/.lore yet — returns the path."""
    _reset()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    home = paths.lore_home()
    assert home == tmp_path / ".lore"


def test_migration_is_idempotent(tmp_path, monkeypatch):
    """Calling lore_home() repeatedly is safe — migration runs at most once."""
    _reset()
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    legacy = tmp_path / ".ai-history"
    legacy.mkdir()
    (legacy / "data").write_text("x", encoding="utf-8")

    first = paths.lore_home()
    second = paths.lore_home()
    assert first == second == tmp_path / ".lore"
    assert (tmp_path / ".lore" / "data").exists()
