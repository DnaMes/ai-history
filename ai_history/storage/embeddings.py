"""Optional local embedding provider for semantic memory recall (#33).

Semantic search needs an embedding model. To keep the base install light,
this is an *optional* feature: it depends on ``fastembed`` (a small
ONNX-runtime model, no torch), pulled in by the ``ai-history[semantic]``
extra. When ``fastembed`` is not installed every function here degrades
gracefully — :func:`embeddings_available` returns False and callers fall
back to FTS search.

Vectors are stored as raw little-endian float32 BLOBs in the
``memory_embeddings`` table (migration 10); similarity is plain cosine,
computed in Python — fine for the few hundred memory rows a user accrues.
"""

from __future__ import annotations

import logging
import math
import struct
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)

# A small, fast, CPU-only model. 384-dimensional output.
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

# Lazily-initialised singleton — building the model is expensive.
_model = None
_model_failed = False


def embeddings_available() -> bool:
    """True if the optional embedding backend can be used.

    Checks that ``fastembed`` is importable. Does not build the model —
    use :func:`embed_text` for that (it builds lazily on first call).
    """
    if _model_failed:
        return False
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model():
    """Return the lazily-built embedding model, or None if unavailable."""
    global _model, _model_failed
    if _model is not None:
        return _model
    if _model_failed:
        return None
    try:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=DEFAULT_MODEL)
        return _model
    except Exception as exc:  # noqa: BLE001 - any failure disables the feature
        logger.warning("Embedding model unavailable, semantic search disabled: %s", exc)
        _model_failed = True
        return None


def embed_text(text: str) -> Optional[List[float]]:
    """Embed a single string. Returns the vector, or None if unavailable.

    A None return is the signal for callers to fall back to FTS search.
    """
    text = (text or "").strip()
    if not text:
        return None
    model = _get_model()
    if model is None:
        return None
    try:
        # fastembed yields numpy arrays; take the first (only) result.
        vectors = list(model.embed([text]))
        if not vectors:
            return None
        return [float(x) for x in vectors[0]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding failed for a text, skipping: %s", exc)
        return None


def pack_vector(vector: Sequence[float]) -> bytes:
    """Pack a float vector into a little-endian float32 BLOB."""
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_vector(blob: bytes) -> List[float]:
    """Unpack a float32 BLOB back into a list of floats."""
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two equal-length vectors (0.0 if either is zero)."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
