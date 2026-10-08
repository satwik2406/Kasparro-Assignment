"""
LLM Adapter module.
Provides an interchangeable interface for LLM scoring (Gemini, OpenAI, or Local/Rule-based Fallback).
Guarantees structured output, strict prompt engineering, and per-candidate error isolation.
"""

import json
import logging
import httpx
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.config import settings

logger = logging.getLogger(__name__)


class LLMScoringOutput(BaseModel):
    """Structured output expected from LLM evaluation."""
    ai_project_depth: int = Field(..., ge=0, le=40, description="Score for AI/Agentic/RAG project depth")
    python_backend: int = Field(..., ge=0, le=30, description="Score for Python & backend engineering")
    cloud_fullstack: int = Field(..., ge=0, le=15, description="Score for Cloud, Docker, and full stack signals")
    engineering_depth: int = Field(..., ge=0, le=5, description="Score for tests, queues, caching, concurrency")
    project_summary: str = Field(..., description="1-2 sentences summarizing candidate's actual project implementations")
    strengths: List[str] = Field(default_factory=list, description="2-3 key technical strengths backed by resume evidence")
    concerns: List[str] = Field(default_factory=list, description="Any gaps, thin wrappers, or missing depth")
    applied_penalties: List[str] = Field(default_factory=list, description="Penalties deducted (e.g., thin wrapper, tutorial copy)")


SCORING_SYSTEM_PROMPT = """You are an expert technical evaluator screening SDE Intern candidates for an advanced Python + AI/Agentic Engineering role.
You will evaluate the candidate resume against a strict 100-point rubric.
Hard requirements have already been validated. Now evaluate technical depth and genuine project quality.

Rubric Categories to score:
1. AI / Agentic / RAG Project Depth (0 to 40 points):
   - Reward real AI systems: stateful agents, RAG, vector retrieval, embeddings, tool-calling, multi-agent orchestration, evaluation (Ragas), business logic.
   - MANDATORY PENALTY: Deduct 5-15 points if an "AI project" is merely a thin wrapper around an LLM API call (e.g., prompt-in-prompt-out Streamlit toy with no retrieval, no state, no tools, no evaluation).
   - PENALTY: Deduct points for tutorial-style projects listed without evidence of ownership or real architecture.
   - Do NOT give full points for framework name dropping without evidence of real usage.
2. Python & Backend Engineering (0 to 30 points):
   - Reward Python, FastAPI, async programming, PostgreSQL, Redis, SQLAlchemy.
   - Reward real project/internship implementation evidence over pure keyword lists.
3. Cloud / Deployment / Full Stack (0 to 15 points):
   - Reward Docker, GCP/AWS, CI/CD, production deployment.
   - React/Next.js are valuable supporting signals when part of an end-to-end full stack system.
4. Engineering Depth Signals (0 to 5 points):
   - Reward automated testing (pytest), caching, message queues (Celery/RabbitMQ), concurrency/async, observability, and robust failure handling.

Return ONLY a valid JSON object matching this schema:
{
  "ai_project_depth": <int 0-40>,
  "python_backend": <int 0-30>,
  "cloud_fullstack": <int 0-15>,
  "engineering_depth": <int 0-5>,
  "project_summary": "<concise evidence-based summary>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "concerns": ["<concern 1>", "<concern 2>"],
  "applied_penalties": ["<reason if penalty applied, or empty>"]
}
"""


class LLMAdapter:
    """Interchangeable LLM provider client with resilient fallback."""

    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        self.openai_api_key = settings.openai_api_key
        self.provider = settings.llm_provider

    async def score_resume(self, candidate_name: str, resume_text: str, matched_skills: List[str]) -> Optional[LLMScoringOutput]:
        """
        Attempts to score the resume using configured LLM provider.
        Returns LLMScoringOutput, or None if no API key is configured or API fails.
        """
        prompt = f"""Candidate Name: {candidate_name}
Matched Skills: {', '.join(matched_skills)}

Resume Text:
---
{resume_text[:4000]}
---
Evaluate this candidate according to the strict rubric. Output valid JSON only."""

        # Try Gemini if configured or auto-detected
        if (self.provider in ["auto", "gemini"]) and self.gemini_api_key:
            try:
                res = await self._call_gemini(prompt)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"Gemini API call failed for {candidate_name}: {e}. Trying fallback.")

        # Try OpenAI if configured
        if (self.provider in ["auto", "openai"]) and self.openai_api_key:
            try:
                res = await self._call_openai(prompt)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"OpenAI API call failed for {candidate_name}: {e}. Trying fallback.")

        return None

    async def _call_gemini(self, prompt: str) -> Optional[LLMScoringOutput]:
        """Call Gemini REST API with JSON mode."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.llm_model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": SCORING_SYSTEM_PROMPT}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(text)
                return LLMScoringOutput.model_validate(parsed_json)
        return None

    async def _call_openai(self, prompt: str) -> Optional[LLMScoringOutput]:
        """Call OpenAI-compatible REST API."""
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(content)
                return LLMScoringOutput.model_validate(parsed_json)
        return None
