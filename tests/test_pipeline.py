"""
Integration tests for the Resume Screening Pipeline.
"""

import pytest
import json
from pathlib import Path
from src.pipeline import ScreeningPipeline


@pytest.mark.asyncio
async def test_pipeline_end_to_end(tmp_path):
    """End-to-end integration test with mixed candidate profiles."""
    resumes_dir = tmp_path / "resumes"
    resumes_dir.mkdir()

    # Candidate 1: Strong AI Engineer
    (resumes_dir / "candidate_01_asha.txt").write_text("""
    Asha Rao
    Email: asha@example.com
    GitHub: https://github.com/asharao
    Skills: Python, FastAPI, PostgreSQL, Redis, LangGraph, Docker, GCP
    Projects: Stateful multi-agent system with Qdrant vector retrieval, tool calling, and Ragas eval.
    """, encoding="utf-8")

    # Candidate 2: Thin Wrapper
    (resumes_dir / "candidate_02_bob.txt").write_text("""
    Bob Wrapper
    Email: bob@example.com
    Skills: Python, Flask
    Projects: Simple prompt wrapper calling OpenAI API in Streamlit.
    """, encoding="utf-8")

    # Candidate 3: Ineligible Java Developer
    (resumes_dir / "candidate_03_carol.txt").write_text("""
    Carol Java
    Email: carol@example.com
    Skills: Java, Spring Boot, React, MySQL
    Projects: Built microservices in Spring Boot with React frontend.
    """, encoding="utf-8")

    # Candidate 4: Malformed 0-byte file
    (resumes_dir / "candidate_04_corrupt.txt").write_text("", encoding="utf-8")

    pipeline = ScreeningPipeline(max_concurrency=2)
    report = await pipeline.run(resumes_dir)

    assert report.summary.total_resumes == 4
    assert report.summary.successfully_parsed == 3
    assert report.summary.eligible == 2
    assert report.summary.rejected == 1
    assert report.summary.failed_unreadable == 1

    # Check ranking order: Asha should be #1, Bob #2
    assert len(report.ranked_candidates) == 2
    assert report.ranked_candidates[0].candidate_name == "Asha Rao"
    assert report.ranked_candidates[0].rank == 1
    assert report.ranked_candidates[1].candidate_name == "Bob Wrapper"
    assert report.ranked_candidates[1].rank == 2

    # Check rejected
    assert len(report.rejected_candidates) == 1
    assert report.rejected_candidates[0].candidate == "Carol Java"

    # Test exports
    json_out = tmp_path / "results.json"
    csv_out = tmp_path / "results.csv"
    pipeline.export_json(report, json_out)
    pipeline.export_csv(report, csv_out)

    assert json_out.exists()
    assert csv_out.exists()

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert "batch_summary" in data
    assert "ranked_shortlist" in data
    assert len(data["ranked_shortlist"]) == 2
