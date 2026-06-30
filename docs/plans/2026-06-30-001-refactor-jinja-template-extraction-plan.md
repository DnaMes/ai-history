---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
product_contract_source: ce-plan-bootstrap
type: refactor
issue: 30
created: 2026-06-30
---

# refactor: Extract Jinja templates from web_templates.py into lore/templates/*.html (#30)

## Summary

`lore/interfaces/web_templates.py` holds 13 Jinja2 templates as 2762 lines of Python
triple-quoted strings. The templates are already valid Jinja2 (they use `{% extends %}`,
`{% include %}`, filters, autoescape). This refactor moves each template into its own
`lore/templates/*.html` file served by a `FileSystemLoader` built **once at import time**,
replacing the current `render()` which rebuilds a Jinja `Environment` on **every request**.
The rendered HTML output must not change (snapshot tests guard this), and all of CSP nonces,
autoescape, the `urlpath` filter, and the `render()` context variables are preserved.

`web_templates.py` is deleted; the two tests that import its `*_TEMPLATE` constants are
switched to read the `.html` files.

---

## Problem Frame

- **Maintainability**: 2762-LOC Python string blob; no editor HTML/Jinja highlighting, no
  templating tooling, awkward diffs. Issue #30 / #25c.
- **Performance bug (incidental, fixed here)**: `web.py:render()` constructs
  `Environment(loader=FunctionLoader(...))` on every call — no template caching/compilation
  reuse. A module-level `Environment` with `FileSystemLoader` compiles once and caches.
- **Already half-wired**: `web.py:152` sets `template_folder=Path(__file__).parent.parent /
  "templates"` (i.e. `lore/templates/`) but the folder doesn't exist and the setting is unused.

---

## Requirements

- **R1** — Each of the 13 templates lives in its own file under `lore/templates/*.html`.
- **R2** — Rendered HTML for every route is byte-identical before/after (snapshot net).
- **R3** — `render()` builds the Jinja `Environment` once (module/app load), not per request.
- **R4** — Preserve: CSP `nonce`, autoescape (`select_autoescape(default_for_string=True,
  default=True)` semantics), the `urlpath` filter, and every context var currently passed
  (`get_style`, `project_label`, `recent`, `provider_tools`, `request`, `nonce`,
  `app_version`, `nav_back`, `show_session_controls`, plus per-call `**kwargs`).
- **R5** — `{% extends %}` / `{% include %}` references resolve correctly. Template names
  become `*.html` and the 3 inheritance strings are updated to match (decision: KTD-1).
- **R6** — `web_templates.py` is deleted; no dangling imports remain. The two tests that
  imported its constants assert against the `.html` files instead (decision: KTD-2).
- **R7** — XSS posture unchanged: nh3 two-pass sanitization and CSP nonce tests stay green.
- **R8** — Full suite green, coverage ≥80% gate, ruff clean.

---

## Key Technical Decisions

**KTD-1 — `.html` files + rewrite the 3 inheritance strings.** Templates are written to
`lore/templates/<name>.html` and the loader is `FileSystemLoader(lore/templates)`. The three
Jinja inheritance references are updated to use the `.html` name:
- `{% extends "base" %}` → `{% extends "base.html" %}` (8 occurrences across the child templates)
- `{% include "session_pairs" %}` → `{% include "session_pairs.html" %}`
- `{% include "session_rows" %}` → `{% include "session_rows.html" %}`

The `render()` template-name argument call sites (`render("session", ...)`, etc. in web.py)
map to filenames via a small name→filename lookup, OR the call sites are updated to pass the
`.html` name. *Rationale*: matches Issue #30's "extract to `*.html`", standard Jinja, gives
editor highlighting. (User-confirmed.)

**KTD-2 — Delete `web_templates.py`; switch the 2 tests to read files.** No re-export shim.
*Rationale*: clean cut, no dead module. `tests/test_vendored_assets.py` (iterates
`dir(web_templates)` for `*_TEMPLATE` attrs) and `tests/test_session_resume.py` (imports
`SESSION_TEMPLATE`, greps strings) are rewritten to read `lore/templates/*.html`. (User-confirmed.)

**KTD-3 — Module-level Environment, lazily built once.** Build the `Environment(loader=
FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(...))` once (module global or a
cached factory), register the `urlpath` filter on it once. `render()` only calls
`env.get_template(name).render(**context)`. *Rationale*: R3, removes the per-request rebuild.
Jinja's own template cache then works (`auto_reload` can stay default; templates are static
files shipped in the wheel).

**KTD-4 — Ship templates in the wheel.** Add `lore/templates/*.html` to
`[tool.setuptools.package-data]` in `pyproject.toml` (alongside the existing
`lore.interfaces` static assets) so `FileSystemLoader` finds them in an installed/Docker
build, not just editable installs. *Rationale*: Docker serves via gunicorn from the installed
package; missing package-data = template-not-found in the container.

---

## High-Level Technical Design

Template inheritance graph (unchanged by the move; only the storage medium changes):

```
base.html
├── session.html         (extends base; includes session_pairs.html)
├── dashboard.html       (extends base)
├── sessions.html        (extends base; includes session_rows.html)
├── projects.html        (extends base)
├── threads.html         (extends base)
├── thread_detail.html   (extends base)
├── rules.html           (extends base)
├── noise_rules.html     (extends base)
├── memory.html          (extends base)
└── stats.html           (extends base)
session_pairs.html       (partial, included by session.html)
session_rows.html        (partial, included by sessions.html)
```

Render path before → after:

```
BEFORE: route → render(name) → build Environment + FunctionLoader(dict)  [EVERY request]
                            → env.get_template(name).render(ctx)

AFTER:  module load → ENV = Environment(FileSystemLoader("lore/templates"))  [ONCE]
                    → ENV.filters["urlpath"] = ...
        route → render(name) → ENV.get_template(f"{name}.html").render(ctx)
```

Context assembly in `render()` (recent sessions, `nav_back`, `show_session_controls`,
`__version__`, nonce, filters) is unchanged — only the Environment construction moves out.

---

## Output Structure

```
lore/templates/
  base.html
  session.html
  session_pairs.html
  session_rows.html
  sessions.html
  dashboard.html
  projects.html
  threads.html
  thread_detail.html
  rules.html
  noise_rules.html
  memory.html
  stats.html
```

---

## Implementation Units

### U1. Snapshot safety net for all rendered routes

**Goal**: Before moving anything, capture the current rendered HTML of every page route so the
refactor can be proven output-neutral (R2).

**Dependencies**: none (do first).

**Files**:
- `tests/test_template_render_snapshots.py` (new)
- fixtures dir e.g. `tests/snapshots/templates/*.html` (generated)

**Approach**: Parametrize over the page routes (`/`, `/sessions`, `/projects`, `/threads`,
`/memory`, `/stats`, `/rules`, `/noise-rules`, a `/session/<id>` and `/thread/<id>` with a
mocked index, plus the `/sessions/rows` and session-pairs fragment). Use the Flask test client
with `load_index` monkeypatched to a small fixed index (reuse the `_EMPTY_INDEX` /
`_index_payload` patterns from `tests/test_api_contract.py` and `tests/test_api_and_mcp.py`).
Normalize the per-request CSP nonce (replace the nonce value with a placeholder) before
comparing, since it varies by request. On first run, write the snapshot; on later runs, assert
equality. Keep these snapshots through the refactor; they are the regression guard.

**Patterns to follow**: `tests/test_render_smoke.py` (live-server render + `_render`),
`tests/test_api_contract.py` `client` fixture (monkeypatched `load_index`).

**Test scenarios**:
- Each page route returns 200 and its normalized HTML equals the stored snapshot.
- `/session/<id>` with a mocked multi-message session renders (covers extends+include path).
- `/sessions/rows` fragment and the session-pairs include render (covers the 2 partials).
- Nonce normalization: two requests to the same route produce equal *normalized* snapshots.
- `Test expectation`: this unit IS the test; verification is that snapshots capture today's output.

**Verification**: `pytest tests/test_template_render_snapshots.py` green against the current
string-based templates (i.e. before any extraction).

---

### U2. Create lore/templates/ and move the 13 templates verbatim

**Goal**: Write each template body to `lore/templates/<name>.html`, byte-for-byte from the
current string constant (minus the Python `"""` wrapper) (R1).

**Dependencies**: U1 (need the net first).

**Files** (new): the 13 files listed in Output Structure.

**Approach**: For each `*_TEMPLATE` constant in `web_templates.py`, write its exact content to
the corresponding `.html` file. Do **not** edit template bodies in this unit except the three
inheritance-string updates (KTD-1): `extends "base"` → `extends "base.html"`,
`include "session_pairs"` → `include "session_pairs.html"`, `include "session_rows"` →
`include "session_rows.html"`. Name mapping (constant → file):
`BASE_TEMPLATE→base.html`, `SESSION_TEMPLATE→session.html`,
`SESSION_PAIRS_TEMPLATE→session_pairs.html`, `SESSION_ROWS_TEMPLATE→session_rows.html`,
`SESSIONS_LIST_TEMPLATE→sessions.html`, `DASHBOARD_TEMPLATE→dashboard.html`,
`PROJECTS_TEMPLATE→projects.html`, `THREADS_LIST_TEMPLATE→threads.html`,
`THREAD_DETAIL_TEMPLATE→thread_detail.html`, `RULES_TEMPLATE→rules.html`,
`NOISE_RULES_TEMPLATE→noise_rules.html`, `MEMORY_TEMPLATE→memory.html`,
`STATS_TEMPLATE→stats.html`.

**Patterns to follow**: existing template names used in `web.py:render()` dict keys (`base`,
`dashboard`, `session`, `session_pairs`, `sessions`, `session_rows`, `projects`, `threads`,
`thread_detail`, `rules`, `noise_rules`, `stats`, `memory`) — the file basenames must match
these keys so the `render()` mapping in U3 stays simple.

**Test scenarios**: `Test expectation: none — pure file move; U1 snapshots + U3 wiring prove
equivalence.`

**Verification**: 13 files exist; each contains the corresponding template body; the three
inheritance strings now carry `.html`. `grep -c` of a distinctive line per template matches the
original.

---

### U3. Rewire render() to a once-built FileSystemLoader Environment

**Goal**: Replace per-request `Environment` + `FunctionLoader(dict)` with a module-level
`Environment` using `FileSystemLoader(lore/templates)`; resolve names to `<name>.html` (R3, R4, R5).

**Dependencies**: U2.

**Files**:
- `lore/interfaces/web.py` (modify `render()`, remove the `templates` dict + per-call
  `Environment`, remove the `from ...web_templates import *_TEMPLATE` block at lines ~87-99)

**Approach**: Add a module-level (or `functools.lru_cache`-wrapped) Environment builder:
`Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(
default_for_string=True, default=True))`, register `env.filters["urlpath"]` once. `TEMPLATES_DIR`
= the existing `Path(__file__).parent.parent / "templates"` (already computed for
`template_folder` at web.py:152 — reuse it). In `render()`, keep all context assembly exactly as
is (recent sessions, nav_back, show_session_controls, version, nonce, the full `.render(...)`
kwarg set) and change only: drop the local `templates` dict and `Environment(...)` construction;
call `ENV.get_template(f"{tpl_name}.html").render(**context)`. Remove the now-unused
`web_templates` imports.

**Patterns to follow**: the current `render()` context block (web.py:506-545) — preserve every
kwarg. Autoescape: `FileSystemLoader` + `.html` files get HTML autoescape via
`select_autoescape` by extension; confirm parity with the prior `default_for_string` behavior
(the string loader autoescaped unconditionally — `.html` files do too, so parity holds).

**Test scenarios**:
- Covers R2: all U1 snapshot tests still pass (output unchanged).
- Covers R3: a test asserting the Environment is built once — e.g. patch/spy that constructing
  the Environment happens at most once across multiple `render()` calls (or assert the module
  global is reused / `get_template` hits the Jinja cache). Right-size: one focused test.
- Covers R5: rendering `session` (extends base + includes session_pairs) and `sessions`
  (includes session_rows) succeed — already exercised by U1 snapshots; add an explicit
  assertion that no `TemplateNotFound` is raised for `base.html` / the partials.
- Edge: calling `render()` outside a request context (nonce fallback to `""`) still works —
  covered by existing `get_csp_nonce` fallback; assert a non-request render path.

**Verification**: U1 snapshots green; `lore-web --port <p>` serves all routes 200; no
`web_templates` symbol referenced anywhere in `lore/` (`grep -rn web_templates lore/` empty).

---

### U4. Delete web_templates.py and migrate the two dependent tests

**Goal**: Remove the dead module and repoint its two importers at the `.html` files (R6).

**Dependencies**: U3 (web.py no longer imports it).

**Files**:
- `lore/interfaces/web_templates.py` (delete)
- `tests/test_session_resume.py` (modify: read `lore/templates/session.html` instead of
  importing `SESSION_TEMPLATE`)
- `tests/test_vendored_assets.py` (modify: iterate `lore/templates/*.html` files instead of
  `dir(web_templates)` `*_TEMPLATE` attrs)

**Approach**: In `test_session_resume.py`, replace
`from lore.interfaces.web_templates import SESSION_TEMPLATE` + string asserts with reading the
file: `(TEMPLATES_DIR / "session.html").read_text()` and the same `assert "resumeSession" in
...` / `"resume-modal"` / `"closeResumeModal"` checks. In `test_vendored_assets.py`, replace the
`dir(web_templates)` loop that pulls `*_TEMPLATE` strings with globbing
`lore/templates/*.html` and reading each file's text — the assertion logic (whatever it checks
about vendored asset references) stays the same, only the source of the HTML strings changes.
Define a shared `TEMPLATES_DIR = Path(...) / "lore" / "templates"` helper in each test (or a
small conftest fixture).

**Patterns to follow**: the existing assertion bodies in both tests — preserve what they check,
change only how they obtain the template text.

**Test scenarios**:
- `test_session_resume.py`: session.html contains `resumeSession`, `Resume`, `resume-modal`,
  `closeResumeModal` (same asserts, file-sourced).
- `test_vendored_assets.py`: the vendored-asset checks run over all 13 `.html` files and pass
  (no CDN refs / nonce presence / whatever it currently asserts — preserve exactly).
- A guard test: `lore/interfaces/web_templates.py` no longer exists / is not importable
  (`importlib.util.find_spec("lore.interfaces.web_templates") is None`).

**Verification**: `grep -rn "web_templates" lore/ tests/` returns nothing; both migrated tests
green.

---

### U5. Package-data + docs update

**Goal**: Ship the templates in the wheel and fix stale docs (R8 + doc hygiene).

**Dependencies**: U2 (files exist).

**Files**:
- `pyproject.toml` (`[tool.setuptools.package-data]`: add `"lore" = ["templates/*.html"]` or
  extend the existing entry)
- `CLAUDE.md` (Package Layout: `web_templates.py` bullet → describe `lore/templates/*.html` +
  the once-built Environment in `web.py:render()`)

**Approach**: Add the template glob to package-data so `FileSystemLoader` resolves in an
installed/Docker context. Update the `CLAUDE.md` "Package Layout" line that currently says
"`web_templates.py` — All HTML/CSS/JS as Python strings…" to reflect the new location and the
no-build-step note (Tailwind/highlight.js still vendored under `lore/interfaces/static/`).

**Patterns to follow**: existing `[tool.setuptools.package-data]` block (it already ships
`lore.interfaces` static `*.js`/`*.css`).

**Test scenarios**: `Test expectation: none — packaging/docs.` Optionally a test that
`importlib.resources` / the `TEMPLATES_DIR` resolves and lists 13 `.html` files (guards the
package-data wiring).

**Verification**: `pip install -e .` then `lore-web` serves 200 (editable); a `docker compose
build app` (or at least `python -c "from lore.interfaces.web import app"` + a render) confirms
templates resolve from the package. `grep` shows no stale `web_templates` reference in docs.

---

## Scope Boundaries

**In scope**: mechanical extraction of the 13 templates to files, the once-built Environment,
deleting `web_templates.py`, migrating the 2 dependent tests, package-data + the one CLAUDE.md
line.

**Out of scope (non-goals)**:
- Any change to template *content*, markup, CSS, or JS (beyond the 3 inheritance-string `.html`
  suffixes). This is output-neutral by design.
- Splitting `base.html` (1640 lines incl. inline CSS/JS) into smaller partials — tempting but a
  separate concern; would change output risk profile. 

### Deferred to Follow-Up Work
- Extracting inline `<style>` / `<script>` from `base.html` into vendored static files
  (separate refactor; needs its own output-neutrality net).
- Jinja template-level caching tuning (`auto_reload=False` in prod) if profiling later shows it
  matters.

---

## System-Wide Impact

- **Docker/gunicorn**: templates must be in the wheel (U5 package-data) — the one cross-cutting
  risk. Verify in an installed context, not just editable.
- **Tests**: `test_render_smoke`, `test_csp_nonces`, `test_session_resume`,
  `test_vendored_assets` all touch this path; U1 snapshots + U4 migrations cover them.
- **Performance**: net positive (Environment built once). No behavior change.

---

## Risks & Dependencies

- **R: TemplateNotFound in Docker** — package-data omission. *Mitigation*: U5 verifies in an
  installed/Docker context, not just editable install.
- **R: autoescape parity** — the string loader used `default_for_string=True`; `.html` files
  use extension-based autoescape. Both HTML-escape. *Mitigation*: U1 snapshots are byte-compared;
  `test_csp_nonces` + nh3 tests (R7) stay green. Any escaping delta shows up as a snapshot diff.
- **R: missed inheritance string** — if one `extends "base"` is left without `.html`,
  `TemplateNotFound`. *Mitigation*: U3 explicit no-`TemplateNotFound` assertion + U1 snapshots
  render every child template.
- **R: repo-autosync staging churn** — known infra gotcha (see HANDOFF.md): before each commit
  run `git diff --cached --name-only` and stage only intended files.

---

## Definition of Done

- 13 templates in `lore/templates/*.html`; `web_templates.py` gone; `grep -rn web_templates
  lore/ tests/` empty.
- `render()` builds the Environment once; all U1 snapshot tests pass (output byte-identical).
- `test_session_resume` + `test_vendored_assets` migrated and green; CSP/nh3 tests green.
- Templates shipped in package-data; verified to resolve in an installed context.
- Full suite green, coverage ≥80%, ruff clean. CLAUDE.md Package Layout updated.
- One PR, squash-merged after CI green.

---

## Sources & Research

- Issue #30 / #25c (the extraction ask).
- `lore/interfaces/web.py:152` (unused `template_folder` already → `lore/templates/`),
  `:490-545` (`render()` with per-request Environment), `:87-99` (`web_templates` imports).
- `lore/interfaces/web_templates.py` (13 `*_TEMPLATE` constants; `extends`/`include` at lines
  1642/1714/2060 etc.).
- Dependent tests: `tests/test_vendored_assets.py:48-60`, `tests/test_session_resume.py:123-134`.
- `tests/test_render_smoke.py`, `tests/test_api_contract.py` (fixture patterns for U1).
