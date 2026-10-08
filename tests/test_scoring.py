"""
Unit tests for Scoring Rubric and Penalties.
"""

import pytest
from src.models import ParsedResume, GitHubSignal
from src.scoring.scorer import CandidateScorer


@pytest.mark.asyncio
async def test_deep_agentic_candidate_scoring():
    """Verify deep agentic candidate receives high score."""
    scorer = CandidateScorer()
    parsed = ParsedResume(
        file_path="resumes/asha.pdf",
        file_name="asha.pdf",
        raw_text="""
        Asha Rao
        Built a stateful multi-agent workflow using LangGraph with tool calling, vector search via Qdrant,
        and automated RAG evaluation using Ragas.
        Backend engineered with FastAPI, PostgreSQL, and Redis caching.
        Containerized with Docker, deployed on GCP with CI/CD. Tested thoroughly using pytest.
        """,
        candidate_name="Asha Rao",
        extracted_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "LangGraph", "Docker", "GCP"]
    )
    gh_signal = GitHubSignal(
        username="asharao",
        profile_found=True,
        total_github_score=8,
        summary="Recently active; 4 maintained Python repositories."
    )

    scored = await scorer.score_candidate(parsed, gh_signal)
    assert scored.eligible is True
    assert scored.total_score >= 75
    assert scored.score_breakdown.ai_project_depth >= 30
    assert scored.score_breakdown.python_backend >= 20
    assert scored.score_breakdown.github == 8
    assert len(scored.applied_penalties) == 0


@pytest.mark.asyncio
async def test_thin_wrapper_penalty():
    """Verify thin wrapper candidate is penalized appropriately."""
    scorer = CandidateScorer()
    parsed = ParsedResume(
        file_path="resumes/wrapper.pdf",
        file_name="wrapper.pdf",
        raw_text="""
        Bob Wrapper
        Python developer.
        Built a simple Streamlit app calling OpenAI API prompt-response with no retrieval, no tools, no agents.
        Used Flask and SQLite.
        """,
        candidate_name="Bob Wrapper",
        extracted_skills=["Python", "Flask"]
    )
    gh_signal = GitHubSignal(total_github_score=2)

    scored = await scorer.score_candidate(parsed, gh_signal)
    assert scored.eligible is True
    # AI project depth must be penalized
    assert scored.score_breakdown.ai_project_depth <= 25
    assert len(scored.applied_penalties) > 0
    assert any("thin" in p.lower() for p in scored.applied_penalties)


@pytest.mark.asyncio
async def test_score_does_not_exceed_100():
    """Score breakdown sum must be capped at 100."""
    scorer = CandidateScorer()
    parsed = ParsedResume(
        file_path="resumes/rockstar.pdf",
        file_name="rockstar.pdf",
        raw_text="""
        Super Developer
        Expert in Python, FastAPI, asyncio, PostgreSQL, Redis, SQLAlchemy, Alembic, Celery,
        LangGraph, LangChain, LlamaIndex, Qdrant, Pinecone, Chroma, tool calling, multi-agent,
        Docker, GCP, AWS, Kubernetes, React, pytest, RabbitMQ, observability, concurrency.
        """,
        candidate_name="Super Developer",
        extracted_skills=["Python", "FastAPI", "LangGraph", "Docker", "GCP", "PostgreSQL", "Redis"]
    )
    gh_signal = GitHubSignal(total_github_score=10)

    scored = await scorer.score_candidate(parsed, gh_signal)
    assert scored.total_score <= 100
    assert scored.total_score >= 85
