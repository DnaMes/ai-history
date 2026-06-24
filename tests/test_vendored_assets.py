"""Tests for vendored web assets — offline / air-gapped support (issue #19).

The web UI must not depend on any CDN: Tailwind and highlight.js are
checked into ``lore/interfaces/static/`` and served by Flask.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from lore.interfaces import web

STATIC_DIR = Path(web.__file__).parent / "static"

VENDORED_FILES = [
    "tailwind-3.4.16.min.js",
    "highlight-11.9.0.min.js",
    "highlight-github-11.9.0.min.css",
]


@pytest.fixture()
def client():
    with web.app.test_client() as c:
        yield c


@pytest.mark.parametrize("name", VENDORED_FILES)
def test_vendored_file_exists(name):
    path = STATIC_DIR / name
    assert path.is_file(), f"missing vendored asset: {path}"
    assert path.stat().st_size > 0


@pytest.mark.parametrize("name", VENDORED_FILES)
def test_static_route_serves_asset(client, name):
    resp = client.get(f"/static/{name}")
    assert resp.status_code == 200
    assert len(resp.data) > 0
    assert resp.data == (STATIC_DIR / name).read_bytes()


def test_templates_reference_no_cdn():
    """No CDN host may appear in any rendered HTML template string."""
    from lore.interfaces import web_templates

    cdn_hosts = (
        "cdn.tailwindcss.com",
        "cdnjs.cloudflare.com",
        "cdn.jsdelivr.net",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
    )
    for attr in dir(web_templates):
        if not attr.endswith("_TEMPLATE"):
            continue
        value = getattr(web_templates, attr)
        if not isinstance(value, str):
            continue
        for host in cdn_hosts:
            assert host not in value, f"{attr} still references CDN host {host}"


def test_dashboard_links_local_assets(client):
    body = client.get("/").get_data(as_text=True)
    assert "/static/tailwind-3.4.16.min.js" in body
    assert "/static/highlight-github-11.9.0.min.css" in body


def test_vendor_manifest_hashes_match():
    """scripts/vendor_assets.py manifest must match the checked-in files."""
    import importlib.util

    script = Path(web.__file__).parents[2] / "scripts" / "vendor_assets.py"
    spec = importlib.util.spec_from_file_location("vendor_assets", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, (_url, expected) in module.ASSETS.items():
        actual = hashlib.sha256((STATIC_DIR / name).read_bytes()).hexdigest()
        assert actual == expected, f"{name}: manifest hash stale"
