"""Shared pytest fixtures and isolation guards."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_embedding_singletons():
    """Reset the embedding-model module singletons between tests.

    `ai_history.storage.embeddings` caches the loaded model in module-level
    globals (`_model`, `_model_failed`). Without this reset, a test that
    simulates a model-build failure would poison every later embeddings
    test depending on run order. The reset keeps tests order-independent.
    """
    from ai_history.storage import embeddings

    saved_model = embeddings._model
    saved_failed = embeddings._model_failed
    yield
    embeddings._model = saved_model
    embeddings._model_failed = saved_failed
