"""Tests puente Teach y embeddings."""

from __future__ import annotations

import numpy as np
import pytest

from forense.app.vision_embed import cosine_similarity, embed_image_bgr, histogram_signature


def test_histogram_signature_stable():
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    img[4:20, 4:20] = (0, 200, 0)
    a = histogram_signature(img)
    b = histogram_signature(img)
    assert len(a) == len(b)
    assert cosine_similarity(a, b) > 0.99


def test_embed_image_bgr_returns_vector():
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    img[:, :] = (40, 120, 200)
    vec, backend = embed_image_bgr(img)
    assert len(vec) > 10
    assert backend in ("clip", "histogram")


def test_cosine_similarity_orthogonal():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) < 0.01
