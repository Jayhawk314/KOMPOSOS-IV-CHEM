# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from fastapi.testclient import TestClient

from api.main import app
from api.rate_limit import get_limiter

get_limiter().burst = 10000
get_limiter().rate = 10000.0

client = TestClient(app)
_HEADERS = {"X-API-Key": "komposos-demo-key"}


def test_compatibility_response_exposes_shared_reasoning_metadata():
    response = client.post(
        "/api/v1/compatibility",
        json={"material_a": "NMC811", "material_b": "EC"},
        headers=_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    scores = data["scores"]

    assert "context" in scores
    assert "calibration" in scores
    assert "ensemble" in scores
    assert "zfc" in scores
    assert isinstance(scores["zfc"]["available"], bool)


def test_zfc_verify_matches_shared_summary_shape():
    response = client.post(
        "/api/v1/zfc-verify",
        json={"material_a": "NMC811", "material_b": "EC"},
        headers=_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()

    assert "available" in data
    assert "num_constraints" in data
    assert "constraints" in data
    assert "has_vetoes" in data
