"""
Scoring Engine implementing the 100-point rubric.
Combines deterministic rubric evaluation with LLM semantic judgment (hybrid approach).
Explainable, evidence-backed, with explicit penalties for thin wrappers and tutorials.
"""

import re
from typing import List, Tuple, Optional
from src.models import ParsedResume, GitHubSignal, ScoreBreakdown, ScoredCandidate
from src.llm.adapter import LLMAdapter, LLMScoringOutput
from src.config import settings

# Deep AI / Agentic systems indicators
AGENTIC_DEEP_MARKERS = [
    "langgraph", "multi-agent", "agentic workflow", "tool calling", "function calling",
    "stateful", "autonomous agent", "ragas", "trulens", "reranker", "hybrid search",
    "chunking strategy", "vector index", "evaluation pipeline"
]

RAG_VECTOR_MARKERS = [
    "rag", "retrieval-augmented", "chromadb", "chroma", "pinecone", "qdrant",
    "weaviate", "faiss", "pgvector", "embeddings", "llamaindex", "langchain"
]

THIN_WRAPPER_INDICATORS = [
    "simple prompt wrapper", "openai api wrapper", "chatgpt wrapper",
    "streamlit app calling openai", "basic prompt-response", "thin wrapper"
]

TUTORIAL_INDICATORS = [
    "youtube clone", "tutorial project", "course project from udemy", "cloned from tutorial"
]

BACKEND_MARKERS = {
    "fastapi": 9,
    "asyncio": 5,
    "async": 4,
    "postgresql": 8,
    "postgres": 8,
    "redis": 6,
    "sqlalchemy": 5,
    "alembic": 4,
    "celery": 5,
    "django": 6,
    "flask": 4
}

CLOUD_MARKERS = {
    "docker": 6,
    "gcp": 5,
    "google cloud": 5,
    "aws": 4,
    "kubernetes": 4,
    "ci/cd": 3,
    "github actions": 3,
    "react": 2,
    "next.js": 2
}

ENGINEERING_DEPTH_MARKERS = {
    "pytest": 2,
    "unit test": 2,
    "integration test": 2,
    "testing": 1,
    "caching": 1,
    "rabbitmq": 2,
    "kafka": 2,
    "observability": 1,
    "prometheus": 1,
    "opentelemetry": 1,
    "logging": 1,
    "rate limiting": 1,
    "circuit breaker": 1,
    "concurrency": 1
}


class CandidateScorer:
    """Evaluates candidates using either LLM or deterministic rule-based engine."""

    def __init__(self):
        self.llm_adapter = LLMAdapter()

    async def score_candidate(self, parsed: ParsedResume, github_signal: GitHubSignal) -> ScoredCandidate:
        """
        Score candidate. Attempts LLM scoring first; falls back to deterministic rule engine seamlessly.
        """
        # Try LLM if available
        llm_output: Optional[LLMScoringOutput] = None
        try:
            llm_output = await self.llm_adapter.score_resume(
                candidate_name=parsed.candidate_name,
                resume_text=parsed.raw_text,
                matched_skills=parsed.extracted_skills
            )
        except Exception:
            llm_output = None

        if llm_output:
            # Construct breakdown using LLM semantic evaluation + GitHub public signal
            breakdown = ScoreBreakdown(
                ai_project_depth=min(40, max(0, llm_output.ai_project_depth)),
                python_backend=min(30, max(0, llm_output.python_backend)),
                cloud_fullstack=min(15, max(0, llm_output.cloud_fullstack)),
                github=github_signal.total_github_score,
                engineering_depth=min(5, max(0, llm_output.engineering_depth))
            )
            total = (
                breakdown.ai_project_depth +
                breakdown.python_backend +
                breakdown.cloud_fullstack +
                breakdown.github +
                breakdown.engineering_depth
            )
            return ScoredCandidate(
                candidate_name=parsed.candidate_name,
                eligible=True,
                total_score=min(100, total),
                score_breakdown=breakdown,
                matched_skills=parsed.extracted_skills,
                project_summary=llm_output.project_summary,
                github_summary=github_signal.summary,
                strengths=llm_output.strengths,
                concerns=llm_output.concerns,
                applied_penalties=llm_output.applied_penalties,
                file_name=parsed.file_name
            )

        # Fallback: Deterministic Explainable Rubric Engine
        return self._deterministic_scoring(parsed, github_signal)

    def _deterministic_scoring(self, parsed: ParsedResume, github_signal: GitHubSignal) -> ScoredCandidate:
        """
        High-precision deterministic rule-based scoring implementing the rubric.
        Extracts evidence directly from text and applies project penalties.
        """
        text_lower = parsed.raw_text.lower()
        applied_penalties: List[str] = []
        strengths: List[str] = []
        concerns: List[str] = []

        # ------------------------------------------------------------------
        # 1. AI / Agentic / RAG Project Depth (0 to 40)
        # ------------------------------------------------------------------
        ai_score = 0
        has_deep_agentic = any(m in text_lower for m in AGENTIC_DEEP_MARKERS)
        has_rag_vector = any(m in text_lower for m in RAG_VECTOR_MARKERS)

        if has_deep_agentic:
            ai_score += 24
            strengths.append("Evidence of advanced agentic systems, tool calling, or multi-agent workflows")
        elif has_rag_vector:
            ai_score += 18
            strengths.append("Practical exposure to RAG pipelines and vector database retrieval")
        else:
            ai_score += 10

        # Additional agentic signals
        for m in ["langgraph", "langchain", "llamaindex", "crewai", "autogen"]:
            if m in text_lower:
                ai_score += 4
                break

        for vdb in ["qdrant", "pinecone", "chroma", "weaviate", "pgvector"]:
            if vdb in text_lower:
                ai_score += 4
                break

        if any(e in text_lower for e in ["ragas", "trulens", "evaluation", "eval"]):
            ai_score += 4
            strengths.append("Includes LLM / RAG evaluation logic")

        if any(tc in text_lower for tc in ["tool calling", "function calling", "tools"]):
            ai_score += 4

        # Penalties: Thin wrapper detection
        is_thin_wrapper = False
        if any(tw in text_lower for tw in THIN_WRAPPER_INDICATORS):
            is_thin_wrapper = True
        elif ("openai" in text_lower or "chatgpt" in text_lower or "gemini" in text_lower) and not has_rag_vector and not has_deep_agentic:
            # Simple API call without RAG or agents
            is_thin_wrapper = True

        if is_thin_wrapper:
            penalty = 12
            ai_score = max(5, ai_score - penalty)
            applied_penalties.append(f"Deducted {penalty} points: Project appears to be a thin LLM API wrapper without state or retrieval")
            concerns.append("AI project lacks complex retrieval, state orchestration, or tool calling")

        # Penalties: Tutorial project detection
        if any(ti in text_lower for ti in TUTORIAL_INDICATORS):
            penalty = 8
            ai_score = max(5, ai_score - penalty)
            applied_penalties.append(f"Deducted {penalty} points: Tutorial-style project without evidence of architecture ownership")
            concerns.append("Projects follow standard tutorial boilerplate")

        ai_score = min(40, max(0, ai_score))

        # ------------------------------------------------------------------
        # 2. Python & Backend Engineering (0 to 30)
        # ------------------------------------------------------------------
        backend_score = 0
        if "fastapi" in text_lower:
            backend_score += 10
            strengths.append("Strong FastAPI backend implementation")
        elif "django" in text_lower or "flask" in text_lower:
            backend_score += 6

        if "postgresql" in text_lower or "postgres" in text_lower:
            backend_score += 8
        elif "mysql" in text_lower or "sqlite" in text_lower:
            backend_score += 4

        if "redis" in text_lower:
            backend_score += 6
        else:
            concerns.append("Limited or missing Redis/caching experience")

        if "async" in text_lower or "asyncio" in text_lower:
            backend_score += 4
        if "sqlalchemy" in text_lower or "alembic" in text_lower:
            backend_score += 4

        backend_score = min(30, max(0, backend_score))

        # ------------------------------------------------------------------
        # 3. Cloud / Deployment / Full Stack (0 to 15)
        # ------------------------------------------------------------------
        cloud_score = 0
        if "docker" in text_lower:
            cloud_score += 6
            strengths.append("Docker containerization experience")
        if "gcp" in text_lower or "google cloud" in text_lower:
            cloud_score += 5
        elif "aws" in text_lower or "azure" in text_lower:
            cloud_score += 4

        if "kubernetes" in text_lower or "k8s" in text_lower or "ci/cd" in text_lower or "github actions" in text_lower:
            cloud_score += 2

        if "react" in text_lower or "next.js" in text_lower:
            cloud_score += 2

        cloud_score = min(15, max(0, cloud_score))

        # ------------------------------------------------------------------
        # 4. GitHub Activity (0 to 10)
        # ------------------------------------------------------------------
        github_score = github_signal.total_github_score

        # ------------------------------------------------------------------
        # 5. Engineering Depth Signals (0 to 5)
        # ------------------------------------------------------------------
        eng_score = 0
        if "pytest" in text_lower or "unit test" in text_lower or "testing" in text_lower:
            eng_score += 2
        if "celery" in text_lower or "rabbitmq" in text_lower or "kafka" in text_lower:
            eng_score += 1
        if "observability" in text_lower or "prometheus" in text_lower or "logging" in text_lower:
            eng_score += 1
        if "concurrency" in text_lower or "rate limit" in text_lower or "error handling" in text_lower:
            eng_score += 1

        eng_score = min(5, max(0, eng_score))

        # Project summary synthesis
        summary_snippets = []
        if has_deep_agentic:
            summary_snippets.append("Built agentic workflows with tool calling and orchestration")
        elif has_rag_vector:
            summary_snippets.append("Developed RAG retrieval system with vector database integration")
        elif is_thin_wrapper:
            summary_snippets.append("Built basic LLM interface/prompt wrapper")
        else:
            summary_snippets.append("Implemented Python backend services with AI model integration")

        project_summary = "; ".join(summary_snippets) + "."

        breakdown = ScoreBreakdown(
            ai_project_depth=ai_score,
            python_backend=backend_score,
            cloud_fullstack=cloud_score,
            github=github_score,
            engineering_depth=eng_score
        )
        total_score = min(100, ai_score + backend_score + cloud_score + github_score + eng_score)

        return ScoredCandidate(
            candidate_name=parsed.candidate_name,
            eligible=True,
            total_score=total_score,
            score_breakdown=breakdown,
            matched_skills=parsed.extracted_skills,
            project_summary=project_summary,
            github_summary=github_signal.summary,
            strengths=strengths[:3] if strengths else ["Python fundamentals"],
            concerns=concerns[:2],
            applied_penalties=applied_penalties,
            file_name=parsed.file_name
        )
