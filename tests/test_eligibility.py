"""
Unit tests for Hard Eligibility Filter.
"""

import pytest
from src.models import ParsedResume
from src.filters.eligibility import evaluate_eligibility


def test_eligible_candidate():
    """Candidate with Python and LangGraph/RAG is eligible."""
    parsed = ParsedResume(
        file_path="resumes/candidate_01.pdf",
        file_name="candidate_01.pdf",
        raw_text="Asha Rao. Experienced in Python, FastAPI, LangGraph, and RAG pipelines using Qdrant.",
        candidate_name="Asha Rao",
        extracted_skills=["Python", "FastAPI", "LangGraph", "RAG"]
    )
    result = evaluate_eligibility(parsed)
    assert result.eligible is True
    assert len(result.rejection_reasons) == 0
    assert result.python_evidence is True
    assert result.ai_agentic_evidence is True


def test_ineligible_java_react_only():
    """Candidate with Java, Spring Boot, React, and no Python or AI is rejected."""
    parsed = ParsedResume(
        file_path="resumes/candidate_java.pdf",
        file_name="candidate_java.pdf",
        raw_text="John Java. Full stack engineer with 3 years of Java, Spring Boot, React, and MySQL.",
        candidate_name="John Java",
        extracted_skills=["Java", "Spring Boot", "React"]
    )
    result = evaluate_eligibility(parsed)
    assert result.eligible is False
    assert len(result.rejection_reasons) == 2
    assert any("Python" in r for r in result.rejection_reasons)
    assert any("AI/agentic" in r for r in result.rejection_reasons)


def test_ineligible_python_only_no_ai():
    """Candidate with strong Python but no AI/LLM/RAG/agents is rejected."""
    parsed = ParsedResume(
        file_path="resumes/candidate_backend.pdf",
        file_name="candidate_backend.pdf",
        raw_text="Dave Backend. Senior Python developer building Django and Flask APIs with PostgreSQL and Redis.",
        candidate_name="Dave Backend",
        extracted_skills=["Python", "Django", "Flask", "PostgreSQL", "Redis"]
    )
    result = evaluate_eligibility(parsed)
    assert result.eligible is False
    assert len(result.rejection_reasons) == 1
    assert any("AI/agentic" in r for r in result.rejection_reasons)


def test_eligible_mixed_stack():
    """Candidate with Java and React, but also Python and LlamaIndex/tools is eligible."""
    parsed = ParsedResume(
        file_path="resumes/candidate_mixed.pdf",
        file_name="candidate_mixed.pdf",
        raw_text="Elena Polyglot. React frontend with Python backend. Built tool calling agent with LlamaIndex.",
        candidate_name="Elena Polyglot",
        extracted_skills=["React", "Python", "LlamaIndex", "Tool Calling"]
    )
    result = evaluate_eligibility(parsed)
    assert result.eligible is True
    assert len(result.rejection_reasons) == 0


def test_malformed_resume_rejected():
    """Malformed or unreadable resume is rejected cleanly."""
    parsed = ParsedResume(
        file_path="resumes/corrupt.pdf",
        file_name="corrupt.pdf",
        raw_text="",
        candidate_name="Corrupt Candidate",
        is_malformed=True,
        parse_error="Empty or corrupt PDF"
    )
    result = evaluate_eligibility(parsed)
    assert result.eligible is False
    assert any("malformed" in r.lower() for r in result.rejection_reasons)
