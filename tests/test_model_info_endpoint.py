"""Tests for GET /api/v1/models (Day 10 Model Performance backend).

Cross-checks against the exact TEST-set numbers confirmed in the Day 5
audit: precision 0.8837, recall 0.7308, f1 0.8000, PR-AUC 0.7602,
ROC-AUC 0.9615, confusion matrix [[42665,5],[14,38]]. If these ever
disagree, something in the pipeline changed -- this test exists to catch
that, not to be loosened to match a drift.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

# Exact Day 5 audit figures.
DAY5_PRECISION = 0.8837209302325582
DAY5_RECALL = 0.7307692307692307
DAY5_F1 = 0.8
DAY5_PR_AUC = 0.7601669751814282
DAY5_ROC_AUC = 0.9615483766292297
DAY5_TN, DAY5_FP, DAY5_FN, DAY5_TP = 42665, 5, 14, 38


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_model_info_matches_day5_test_set_audit_exactly(client):
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    body = response.json()

    assert body["precision"] == pytest.approx(DAY5_PRECISION)
    assert body["recall"] == pytest.approx(DAY5_RECALL)
    assert body["f1"] == pytest.approx(DAY5_F1)
    assert body["pr_auc"] == pytest.approx(DAY5_PR_AUC)
    assert body["roc_auc"] == pytest.approx(DAY5_ROC_AUC)

    assert body["tp"] == DAY5_TP
    assert body["fp"] == DAY5_FP
    assert body["fn"] == DAY5_FN
    assert body["tn"] == DAY5_TN

    expected_fpr = DAY5_FP / (DAY5_FP + DAY5_TN)
    expected_fnr = DAY5_FN / (DAY5_FN + DAY5_TP)
    assert body["false_positive_rate"] == pytest.approx(expected_fpr)
    assert body["false_negative_rate"] == pytest.approx(expected_fnr)


def test_model_info_includes_metadata(client):
    response = client.get("/api/v1/models")
    body = response.json()
    assert body["model_version"] == "fraud_model_v1"
    assert body["threshold"] == pytest.approx(0.5)
    assert "training_date" in body
    assert "dataset_version" in body
    assert body["test_set_size"] == DAY5_TN + DAY5_FP + DAY5_FN + DAY5_TP
