"""
API integration tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health check returns ok and configuration."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "weights" in data
    assert data["weights"]["ai_project_depth"] == 40


def test_screen_and_results_flow(tmp_path):
    """Test POST /screen and subsequent GET /results."""
    resumes_dir = tmp_path / "resumes"
    resumes_dir.mkdir()
    (resumes_dir / "candidate_api.txt").write_text("""
    Priya Sharma
    Email: priya@example.com
    GitHub: https://github.com/priyasharma
    Skills: Python, FastAPI, LangGraph, PostgreSQL, Docker, GCP
    Projects: Multi-agent support automation with CrewAI and FastAPI.
    """, encoding="utf-8")

    out_file = tmp_path / "output.json"

    # Call POST /screen
    response = client.post("/screen", json={
        "input_dir": str(resumes_dir),
        "output_file": str(out_file),
        "max_concurrency": 2
    })
    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["total_resumes"] == 1
    assert report["summary"]["eligible"] == 1
    assert len(report["ranked_candidates"]) == 1
    assert report["ranked_candidates"][0]["candidate_name"] == "Priya Sharma"

    # Call GET /results
    get_res = client.get("/results")
    assert get_res.status_code == 200
    assert get_res.json()["summary"]["total_resumes"] == 1
