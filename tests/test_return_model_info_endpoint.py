"""Tests for GET /api/v1/models/return (Tier 2 return-risk scorer).

Mirrors tests/test_model_info_endpoint.py's pattern exactly: cross-checks
against the exact TEST-set numbers this project's own training run
produced. If these ever disagree, something in the pipeline changed --
this test exists to catch that, not to be loosened to match a drift.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

# Exact figures from this project's own train_return_model.py run,
# confirmed live against the return-risk audit report.
AUDIT_PRECISION = 0.64
AUDIT_RECALL = 0.5387205387205387
AUDIT_F1 = 0.5850091407678245
AUDIT_PR_AUC = 0.6650311153292932
AUDIT_ROC_AUC = 0.8234446018759743
AUDIT_TN, AUDIT_FP, AUDIT_FN, AUDIT_TP = 2955, 360, 548, 640


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_return_model_info_matches_audited_test_set_numbers(client):
    response = client.get("/api/v1/models/return")
    assert response.status_code == 200
    body = response.json()

    assert body["precision"] == pytest.approx(AUDIT_PRECISION)
    assert body["recall"] == pytest.approx(AUDIT_RECALL)
    assert body["f1"] == pytest.approx(AUDIT_F1)
    assert body["pr_auc"] == pytest.approx(AUDIT_PR_AUC)
    assert body["roc_auc"] == pytest.approx(AUDIT_ROC_AUC)

    assert body["tp"] == AUDIT_TP
    assert body["fp"] == AUDIT_FP
    assert body["fn"] == AUDIT_FN
    assert body["tn"] == AUDIT_TN

    expected_fpr = AUDIT_FP / (AUDIT_FP + AUDIT_TN)
    expected_fnr = AUDIT_FN / (AUDIT_FN + AUDIT_TP)
    assert body["false_positive_rate"] == pytest.approx(expected_fpr)
    assert body["false_negative_rate"] == pytest.approx(expected_fnr)


def test_return_model_info_includes_metadata_and_honesty_note(client):
    response = client.get("/api/v1/models/return")
    body = response.json()
    assert body["model_version"] == "return_model_v1"
    assert body["threshold"] == pytest.approx(0.5)
    assert "training_date" in body
    assert "UCI Online Retail II" in body["dataset_version"]
    # Never confused with the fraud model's dataset.
    assert "ULB" not in body["dataset_version"]
    assert "creditcard" not in body["dataset_version"]
    # The honesty caveat is a real field on the response, not just a
    # code comment -- confirm it says what it needs to say.
    assert "smaller, less-established dataset" in body["dataset_honesty_note"]
    assert "proxy" in body["dataset_honesty_note"]
    assert body["test_set_size"] == AUDIT_TN + AUDIT_FP + AUDIT_FN + AUDIT_TP


def test_fraud_and_return_model_info_are_never_blended(client):
    """The two models' metrics must come back as two distinct payloads,
    never merged into one response -- see api/routes/return_model_info.py's
    docstring for why this separation was a deliberate design choice.
    """
    fraud = client.get("/api/v1/models").json()
    returns = client.get("/api/v1/models/return").json()

    assert fraud["model_version"] != returns["model_version"]
    assert fraud["dataset_version"] != returns["dataset_version"]
    assert "dataset_honesty_note" not in fraud
