"""
Data models and schemas for Resume Screening & Ranking System.
Strict Pydantic schemas adhering to assignment requirements.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ParsedResume(BaseModel):
    """Raw extracted information from a resume file."""
    file_path: str
    file_name: str
    raw_text: str
    candidate_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)
    project_snippets: List[str] = Field(default_factory=list)
    is_malformed: bool = False
    parse_error: Optional[str] = None


class EligibilityResult(BaseModel):
    """Hard filter decision output."""
    candidate: str
    eligible: bool
    rejection_reasons: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    python_evidence: bool = False
    ai_agentic_evidence: bool = False


class GitHubSignal(BaseModel):
    """Signals extracted from public GitHub profile."""
    username: Optional[str] = None
    profile_found: bool = False
    public_repos_count: int = 0
    maintained_relevant_repos: int = 0
    recent_events_count: int = 0
    recent_activity_score: int = Field(default=0, ge=0, le=5)
    relevant_repo_score: int = Field(default=0, ge=0, le=5)
    total_github_score: int = Field(default=0, ge=0, le=10)
    summary: str = "No GitHub profile provided or profile unavailable."
    enrichment_status: str = "skipped"  # "success", "failed", "rate_limited", "not_found", "skipped"


class ScoreBreakdown(BaseModel):
    """Breakdown across the 5 evaluation categories (100 total points)."""
    ai_project_depth: int = Field(..., ge=0, le=40, description="Real AI systems, agents, RAG, tools, orchestration")
    python_backend: int = Field(..., ge=0, le=30, description="Python, FastAPI, async, PostgreSQL, Redis")
    cloud_fullstack: int = Field(..., ge=0, le=15, description="GCP, Docker, deployment, full stack React/Next.js")
    github: int = Field(..., ge=0, le=10, description="Public GitHub activity and maintained repos")
    engineering_depth: int = Field(..., ge=0, le=5, description="Testing, queues, caching, architecture, failure handling")


class ScoredCandidate(BaseModel):
    """Full evaluation record for an eligible candidate."""
    rank: Optional[int] = None
    candidate_name: str
    eligible: bool = True
    total_score: int
    score_breakdown: ScoreBreakdown
    matched_skills: List[str]
    project_summary: str
    github_summary: str
    strengths: List[str]
    concerns: List[str]
    applied_penalties: List[str] = Field(default_factory=list)
    file_name: Optional[str] = None


class RejectedCandidate(BaseModel):
    """Record for an ineligible candidate."""
    candidate: str
    eligible: bool = False
    rejection_reasons: List[str]
    matched_skills: List[str]
    file_name: Optional[str] = None


class BatchSummary(BaseModel):
    """Overall batch statistics."""
    total_resumes: int
    successfully_parsed: int
    eligible: int
    rejected: int
    failed_unreadable: int
    execution_time_seconds: float = 0.0


class ScreeningReport(BaseModel):
    """Complete output produced by the screening pipeline."""
    summary: BatchSummary
    ranked_candidates: List[ScoredCandidate]
    rejected_candidates: List[RejectedCandidate]
    failed_files: List[Dict[str, str]] = Field(default_factory=list)
