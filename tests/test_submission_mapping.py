"""Tests for Tier 3D's problem-statement mapping page
(frontend/src/pages/SubmissionMapping.tsx).

No frontend test framework exists in this project -- frontend/package.json
has none, and pytest + live Puppeteer/manual verification has been this
project's established testing convention through every prior tier. So a
Python test can't literally "render" the React page. What it CAN do, and
what actually matters for the specific risk this Tier called out ("a
stale/hardcoded number here would be a real, embarrassing inconsistency
if a judge cross-checks it against Model Performance"), is two things:

1. A contract test: confirm the two live endpoints the page depends on
   (GET /api/v1/models, GET /api/v1/models/return) still return every
   field the page reads, with sane values. If either endpoint's shape
   ever changes, this fails loudly instead of the page silently breaking.

2. A static anti-drift check on the page's own source: confirm it reads
   every metric through the live API response objects
   (modelInfo.data.____, returnModelInfo.data.____), and confirm none of
   the metric-shaped literal numbers from the original brief (88.4, 73.1,
   0.760, 0.962, 64.00, 53.87, 0.8234) appear as hardcoded text anywhere
   in the component. This is actually a STRONGER guarantee against silent
   drift than a render test would give: a render test only proves the
   page currently shows the right number, not that a future edit couldn't
   quietly replace a live read with a hardcoded copy that happens to
   match today's value.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBMISSION_PAGE_PATH = (
    PROJECT_ROOT / "frontend" / "src" / "pages" / "SubmissionMapping.tsx"
)

# The exact figures named in the Tier 3D brief -- if any of these appear as
# literal text in the component, someone hardcoded a copy instead of
# reading it live.
BRIEF_LITERAL_NUMBERS = ["88.4", "73.1", "0.760", "0.962", "64.00", "53.87", "0.8234"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def submission_page_source() -> str:
    assert SUBMISSION_PAGE_PATH.exists(), (
        f"Expected {SUBMISSION_PAGE_PATH} to exist -- has the page been renamed/moved? "
        "This test would otherwise silently pass having checked nothing."
    )
    return SUBMISSION_PAGE_PATH.read_text(encoding="utf-8")


def test_model_info_endpoint_returns_every_field_the_page_reads(client):
    """Contract test: GET /api/v1/models must keep returning what
    SubmissionMapping.tsx reads for "The Bar"'s precision/recall item.
    """
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    body = response.json()

    for field in ("precision", "recall", "pr_auc", "roc_auc", "test_set_size"):
        assert field in body, f"GET /api/v1/models is missing '{field}' -- the submission page reads this"

    # Sanity ranges, not exact-value pins (test_model_info_endpoint.py
    # already owns exact-value regression coverage against the Day 5
    # audit) -- this test's job is the CONTRACT, not the number itself.
    assert 0.0 <= body["precision"] <= 1.0
    assert 0.0 <= body["recall"] <= 1.0
    assert 0.0 <= body["pr_auc"] <= 1.0
    assert 0.0 <= body["roc_auc"] <= 1.0
    assert body["test_set_size"] > 0


def test_return_model_info_endpoint_returns_every_field_the_page_reads(client):
    """Contract test: GET /api/v1/models/return must keep returning the
    dataset_honesty_note SubmissionMapping.tsx quotes verbatim for the
    return-risk scorer's caveat.
    """
    response = client.get("/api/v1/models/return")
    assert response.status_code == 200
    body = response.json()

    assert "dataset_honesty_note" in body
    assert isinstance(body["dataset_honesty_note"], str)
    assert len(body["dataset_honesty_note"]) > 0


def test_submission_page_reads_metrics_live_not_hardcoded(submission_page_source):
    source = submission_page_source

    # Must actually call the live fetchers Model Performance itself uses --
    # not a separate/parallel data source.
    assert "getModelInfo" in source
    assert "getReturnModelInfo" in source

    # Must read the specific fields "The Bar" quotes, off the live response
    # objects (modelInfo.data.___ / returnModelInfo.data.___), not a local
    # constant.
    for field in ("precision", "recall", "pr_auc", "roc_auc"):
        assert f"modelInfo.data.{field}" in source, (
            f"Expected the page to read {field} from the live modelInfo response, "
            "not a hardcoded value"
        )
    assert "returnModelInfo.data.dataset_honesty_note" in source


def test_submission_page_contains_no_hardcoded_metric_literals(submission_page_source):
    source = submission_page_source
    for literal in BRIEF_LITERAL_NUMBERS:
        assert literal not in source, (
            f"Found the literal '{literal}' in SubmissionMapping.tsx -- this looks like a "
            "hardcoded copy of a metric that should be read live instead, exactly the drift "
            "risk this test exists to catch."
        )
