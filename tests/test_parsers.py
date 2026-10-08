"""
Unit tests for Resume Parsers and Metadata Extractor.
"""

import pytest
from pathlib import Path
from src.parsers.extractor import (
    extract_candidate_name,
    extract_github_info,
    extract_skills_and_keywords,
    parse_resume_file
)
from src.parsers.txt_parser import TXTParser


def test_txt_parser_and_metadata(tmp_path):
    """Test text resume parsing and extraction of entities."""
    file = tmp_path / "candidate_01_Asha_Rao.txt"
    file.write_text(
        """Asha Rao
Email: asha.rao@example.com
Phone: (555) 123-4567
GitHub: https://github.com/asharao
LinkedIn: https://linkedin.com/in/asharao

Skills: Python, FastAPI, PostgreSQL, Redis, LangGraph, Docker, GCP

Projects:
Built a multi-agent RAG workflow with tool calling and Qdrant vector database.
""",
        encoding="utf-8"
    )

    parsed = parse_resume_file(file)
    assert parsed.is_malformed is False
    assert parsed.candidate_name == "Asha Rao"
    assert parsed.email == "asha.rao@example.com"
    assert parsed.github_username == "asharao"
    assert "Python" in parsed.extracted_skills
    assert "FastAPI" in parsed.extracted_skills
    assert "LangGraph" in parsed.extracted_skills


def test_empty_file_isolated(tmp_path):
    """Test empty file does not crash and marks as malformed."""
    empty_file = tmp_path / "empty_resume.txt"
    empty_file.write_text("", encoding="utf-8")

    parsed = parse_resume_file(empty_file)
    assert parsed.is_malformed is True
    assert "empty" in parsed.parse_error.lower()


def test_github_extraction_variants():
    """Test various GitHub handle and URL representations."""
    url1, user1 = extract_github_info("Check out my github.com/johndoe profile")
    assert user1 == "johndoe"

    url2, user2 = extract_github_info("GitHub: @sarah_connor on web")
    assert user2 == "sarah_connor"

    url3, user3 = extract_github_info("No profile here")
    assert user3 is None
