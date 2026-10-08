"""
Deterministic Hard Eligibility Rules for Resume Screening.
A candidate MUST satisfy both Python evidence and AI/agentic project evidence.
"""

import re
from typing import List, Tuple
from src.models import ParsedResume, EligibilityResult


# Primary Python markers (language and ecosystem)
PYTHON_KEYWORDS = {
    "python", "python3", "fastapi", "django", "flask", "pytorch",
    "sqlalchemy", "pydantic", "celery", "asyncio", "pandas", "numpy",
    "scikit-learn", "uvicorn", "alembic", "pytest"
}

# Strong AI / LLM / RAG / Agentic indicators
AI_AGENTIC_KEYWORDS = {
    # Agentic frameworks
    "langchain", "langgraph", "llamaindex", "llama-index", "google adk",
    "crewai", "autogen", "semantic kernel",
    # Core RAG / Retrieval / Vector
    "rag", "retrieval-augmented generation", "retrieval augmented generation",
    "vector search", "vector database", "embeddings", "sentence-transformers",
    "chromadb", "chroma", "pinecone", "qdrant", "weaviate", "faiss", "pgvector", "milvus",
    # Agentic mechanisms
    "tool calling", "function calling", "tool-calling", "agentic", "agents",
    "multi-agent", "autonomous agent", "agentic workflow", "stateful workflow",
    # Evaluation, models & tuning
    "ragas", "trulens", "deepseek", "gpt-4", "gpt-3.5", "claude", "gemini",
    "openai", "llm", "chatgpt", "genai", "large language model",
    "llm evaluation", "prompt engineering", "fine-tuning", "lora", "qlora",
    "huggingface", "transformers", "ollama", "vllm"
}

# Regex word boundary pattern builder
def _contains_any_word(text_lower: str, keywords: set) -> List[str]:
    matched = []
    for kw in sorted(keywords):
        if len(kw) <= 4:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_lower):
                matched.append(kw)
        else:
            if kw in text_lower:
                matched.append(kw)
    return matched


def evaluate_eligibility(parsed: ParsedResume) -> EligibilityResult:
    """
    Evaluates candidate eligibility against strict rule-based filters.
    Candidates must demonstrate:
      1. Genuine Python stack evidence.
      2. Genuine AI / LLM / RAG / Agentic evidence.
    """
    if parsed.is_malformed:
        return EligibilityResult(
            candidate=parsed.candidate_name,
            eligible=False,
            rejection_reasons=[f"File unreadable or malformed: {parsed.parse_error}"],
            matched_skills=[],
            python_evidence=False,
            ai_agentic_evidence=False
        )

    text_lower = parsed.raw_text.lower()
    matched_python = _contains_any_word(text_lower, PYTHON_KEYWORDS)
    matched_ai = _contains_any_word(text_lower, AI_AGENTIC_KEYWORDS)

    # Check for genuine Python evidence
    has_python_evidence = len(matched_python) > 0
    # Additional sanity: ensure 'python' specifically or python framework is present
    if not has_python_evidence:
        # Check if skills list explicitly extracted Python
        has_python_evidence = any("python" in s.lower() for s in parsed.extracted_skills)

    # Check for genuine AI / Agentic evidence
    # Must have at least one meaningful agentic/RAG/AI concept or framework
    has_ai_evidence = len(matched_ai) > 0

    rejection_reasons: List[str] = []
    if not has_python_evidence:
        rejection_reasons.append("No evidence of Python stack (Python must be a genuine skill, project, or work language)")

    if not has_ai_evidence:
        rejection_reasons.append("No AI/agentic project or framework evidence (Missing RAG, agents, LangChain/LangGraph, embeddings, or LLM systems)")

    is_eligible = has_python_evidence and has_ai_evidence

    return EligibilityResult(
        candidate=parsed.candidate_name,
        eligible=is_eligible,
        rejection_reasons=rejection_reasons,
        matched_skills=parsed.extracted_skills,
        python_evidence=has_python_evidence,
        ai_agentic_evidence=has_ai_evidence
    )
