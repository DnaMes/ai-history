"""Utility functions for web interface.

This module contains:
- Rate limiting utilities
- Metrics tracking
- Noise rules management
- Request ID generation
"""

import json
import logging
import os
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Optional

from flask import request

# ActionJobCancelledError is defined in the framework-free service layer
# (issue #47) so both ``services`` and the interface modules share one
# exception type. Re-exported here for backwards compatibility — callers
# and tests historically import it from ``web_utils``.
from ai_history.services import ActionJobCancelledError  # noqa: F401

logger = logging.getLogger(__name__)

# Rate limiting state
RATE_LIMIT_STATE: dict[tuple[str, str], list[float]] = {}
RATE_LIMIT_LOCK = Lock()
RATE_LIMIT_BUCKET_TTL_SECONDS = 3600

# Metrics state
METRICS: dict[str, int] = {}
METRICS_LOCK = Lock()

# Paths
OUTPUT_DIR = Path.home() / ".ai-history"
NOISE_RULES_PATH = OUTPUT_DIR / "noise_rules.json"


class ActionJobTimeoutError(RuntimeError):
    pass


def _rate_limit_enabled() -> bool:
    raw = (os.environ.get("AI_HISTORY_RATE_LIMIT_ENABLED") or "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = (os.environ.get(name) or str(default)).strip()
    try:
        return max(minimum, int(raw))
    except ValueError:
        logger.warning("Invalid %s=%r, using default %s", name, raw, default)
        return default


def _rate_limit_window_seconds() -> int:
    return _env_int("AI_HISTORY_RATE_LIMIT_WINDOW_SECONDS", 60, minimum=1)


def _rate_limit_max_for_path(path: str) -> int:
    normalized = path.strip()
    if normalized == "/api/reload-sessions":
        return _env_int("AI_HISTORY_RATE_LIMIT_RELOAD_PER_WINDOW", 12, minimum=1)
    if normalized == "/api/audit":
        return _env_int("AI_HISTORY_RATE_LIMIT_AUDIT_PER_WINDOW", 20, minimum=1)
    if normalized == "/api/search":
        return _env_int("AI_HISTORY_RATE_LIMIT_SEARCH_PER_WINDOW", 180, minimum=1)
    return _env_int("AI_HISTORY_RATE_LIMIT_MAX_API_REQUESTS", 240, minimum=1)


def _client_ip() -> str:
    # Only read X-Forwarded-For / X-Real-IP when running behind a trusted proxy.
    # If the app is exposed directly, these headers can be spoofed by any client.
    # Set TRUSTED_PROXY=1 (or any non-empty value) when a reverse proxy is in front.
    if os.environ.get("TRUSTED_PROXY"):
        forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
        real_ip = (request.headers.get("X-Real-IP") or "").strip()
        if real_ip:
            return real_ip
    return request.remote_addr or "unknown"


def _should_rate_limit(path: str) -> bool:
    if not path.startswith("/api/"):
        return False
    return path not in {"/api/build-info", "/api/health", "/api/ready", "/api/live"}


def _consume_rate_limit(
    path: str, client_ip: str, now_epoch: Optional[float] = None
) -> tuple[bool, int, int, int, int]:
    now = now_epoch if now_epoch is not None else time.time()
    window = _rate_limit_window_seconds()
    max_requests = _rate_limit_max_for_path(path)
    cutoff = now - window
    stale_cutoff = now - RATE_LIMIT_BUCKET_TTL_SECONDS
    key = (client_ip, path)

    with RATE_LIMIT_LOCK:
        stale_keys: list[tuple[str, str]] = []
        for bucket_key, bucket in RATE_LIMIT_STATE.items():
            fresh = [stamp for stamp in bucket if stamp >= stale_cutoff]
            if fresh:
                RATE_LIMIT_STATE[bucket_key] = fresh
            else:
                stale_keys.append(bucket_key)
        for bucket_key in stale_keys:
            RATE_LIMIT_STATE.pop(bucket_key, None)

        bucket = [stamp for stamp in RATE_LIMIT_STATE.get(key, []) if stamp >= cutoff]
        if len(bucket) >= max_requests:
            oldest = bucket[0]
            retry_after = max(1, int(window - (now - oldest)))
            RATE_LIMIT_STATE[key] = bucket
            reset_in = retry_after
            return False, retry_after, 0, max_requests, reset_in

        bucket.append(now)
        RATE_LIMIT_STATE[key] = bucket
        remaining = max(0, max_requests - len(bucket))
        reset_in = max(1, int(window - (now - bucket[0]))) if bucket else window
        return True, 0, remaining, max_requests, reset_in


def _request_id() -> str:
    value = (request.headers.get("X-Request-ID") or "").strip()
    if not value:
        value = f"req-{uuid.uuid4().hex[:16]}"
    return value[:128]


def _metrics_inc(key: str, amount: int = 1) -> None:
    with METRICS_LOCK:
        METRICS[key] = int(METRICS.get(key, 0)) + int(amount)


def _metrics_snapshot() -> dict[str, int]:
    with METRICS_LOCK:
        return {k: int(v) for k, v in METRICS.items()}


def _record_job_outcome(kind: str, status: str, started_epoch: float) -> None:
    duration_ms = max(0, int((time.time() - started_epoch) * 1000))
    prefix = "reload" if kind == "reload" else "audit"

    _metrics_inc(f"{prefix}_jobs_duration_ms_total", duration_ms)
    if status == "completed":
        _metrics_inc(f"{prefix}_jobs_completed")
    elif status == "cancelled":
        _metrics_inc(f"{prefix}_jobs_cancelled")
    else:
        _metrics_inc(f"{prefix}_jobs_failed")


def _json_request_logging_enabled() -> bool:
    raw = (os.environ.get("AI_HISTORY_JSON_REQUEST_LOGS") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _default_noise_rules() -> dict:
    return {
        "default": {
            "strip_ansi_sequences": True,
        },
        "claude-code": {
            "claude_strip_command_xml": True,
            "claude_summarize_file_operations": True,
        },
        "cursor": {
            "cursor_summarize_file_operations": True,
        },
        "gemini-cli": {
            "gemini_summarize_file_operations": True,
        },
        "codex": {
            "codex_summarize_file_operations": True,
        },
        "copilot-cli": {
            "copilot_summarize_file_operations": True,
        },
        "vscode-copilot": {
            "vscode_summarize_file_operations": True,
        },
        "opencode": {
            "opencode_strip_user_caveat": True,
            "opencode_summarize_file_operations": True,
            "opencode_summarize_unset_env_vars": True,
        },
        "antigravity": {
            "antigravity_summarize_file_operations": True,
        },
        "warp": {
            "warp_drop_toolu_noise": True,
            "warp_summarize_file_operations": True,
        },
    }


def _noise_rule_presets() -> dict:
    balanced = _default_noise_rules()

    aggressive = _default_noise_rules()
    for provider_rules in aggressive.values():
        if not isinstance(provider_rules, dict):
            continue
        for key in list(provider_rules.keys()):
            provider_rules[key] = True

    minimal = _default_noise_rules()
    for provider, provider_rules in minimal.items():
        if not isinstance(provider_rules, dict):
            continue
        for key in list(provider_rules.keys()):
            provider_rules[key] = provider == "default" and key == "strip_ansi_sequences"

    return {
        "balanced": {
            "label": "Balanced",
            "description": "Recommended default cleanup",
            "rules": balanced,
        },
        "aggressive": {
            "label": "Aggressive Cleanup",
            "description": "Hide most repetitive operational noise",
            "rules": aggressive,
        },
        "minimal": {
            "label": "Minimal Cleanup",
            "description": "Keep transcript mostly raw",
            "rules": minimal,
        },
    }


def load_noise_rules() -> dict:
    defaults = _default_noise_rules()
    if not NOISE_RULES_PATH.exists():
        return defaults
    try:
        with open(NOISE_RULES_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        logger.warning("Failed to load noise rules from %s: %s", NOISE_RULES_PATH, exc)
        return defaults

    if not isinstance(data, dict):
        return defaults

    merged = _default_noise_rules()
    for provider, rules in data.items():
        if not isinstance(provider, str) or not isinstance(rules, dict):
            continue
        dst = merged.setdefault(provider, {})
        for key, value in rules.items():
            if isinstance(key, str) and isinstance(value, bool):
                dst[key] = value
    return merged


def save_noise_rules(payload: dict) -> dict:
    current = _default_noise_rules()
    if isinstance(payload, dict):
        for provider, rules in payload.items():
            if not isinstance(provider, str) or not isinstance(rules, dict):
                continue
            dst = current.setdefault(provider, {})
            for key, value in rules.items():
                if isinstance(key, str) and isinstance(value, bool):
                    dst[key] = value

    NOISE_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOISE_RULES_PATH, "w", encoding="utf-8") as handle:
        json.dump(current, handle, indent=2, sort_keys=True)
    return current
