"""
Pipeline Orchestrator.
Coordinates ingestion, parsing, hard filtering, GitHub enrichment, scoring, and ranking.
Handles malformed resumes, bounded concurrency, and structured exports.
"""

import os
import csv
import json
import time
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import settings
from src.models import (
    ParsedResume, EligibilityResult, ScoredCandidate, RejectedCandidate,
    BatchSummary, ScreeningReport
)
from src.parsers.extractor import parse_resume_file
from src.filters.eligibility import evaluate_eligibility
from src.enrichment.github import fetch_github_signals
from src.scoring.scorer import CandidateScorer


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


class ScreeningPipeline:
    """End-to-end resume screening and ranking pipeline."""

    def __init__(self, max_concurrency: Optional[int] = None):
        self.semaphore = asyncio.Semaphore(max_concurrency or settings.max_concurrency)
        self.scorer = CandidateScorer()

    async def run(self, input_dir: Path) -> ScreeningReport:
        """Process all resumes in input_dir and return complete ScreeningReport."""
        start_time = time.time()

        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

        # Ingest files
        all_files = [
            f for f in input_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        # Deduplicate files by content hash to prevent processing exact duplicate files
        unique_files: List[Path] = []
        seen_hashes = set()
        for f in sorted(all_files):
            try:
                content_bytes = f.read_bytes()
                file_hash = hashlib.md5(content_bytes).hexdigest()
                if file_hash not in seen_hashes:
                    seen_hashes.add(file_hash)
                    unique_files.append(f)
            except Exception:
                # Include for parsing so it properly records as unreadable
                unique_files.append(f)

        total_resumes = len(unique_files)
        tasks = [self._process_single_resume(file_path) for file_path in unique_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scored_candidates: List[ScoredCandidate] = []
        rejected_candidates: List[RejectedCandidate] = []
        failed_files: List[Dict[str, str]] = []

        successfully_parsed_count = 0

        for res in results:
            if isinstance(res, Exception):
                failed_files.append({"file": "unknown", "error": str(res)})
                continue

            status, data = res
            if status == "failed":
                failed_files.append(data)
            elif status == "rejected":
                successfully_parsed_count += 1
                rejected_candidates.append(data)
            elif status == "eligible":
                successfully_parsed_count += 1
                scored_candidates.append(data)

        # Rank eligible candidates descending by total_score
        # Secondary sort by ai_project_depth, then python_backend
        scored_candidates.sort(
            key=lambda c: (
                c.total_score,
                c.score_breakdown.ai_project_depth,
                c.score_breakdown.python_backend,
                c.score_breakdown.engineering_depth
            ),
            reverse=True
        )

        for rank_idx, candidate in enumerate(scored_candidates, start=1):
            candidate.rank = rank_idx

        elapsed = round(time.time() - start_time, 2)

        summary = BatchSummary(
            total_resumes=total_resumes,
            successfully_parsed=successfully_parsed_count,
            eligible=len(scored_candidates),
            rejected=len(rejected_candidates),
            failed_unreadable=len(failed_files),
            execution_time_seconds=elapsed
        )

        return ScreeningReport(
            summary=summary,
            ranked_candidates=scored_candidates,
            rejected_candidates=rejected_candidates,
            failed_files=failed_files
        )

    async def _process_single_resume(self, file_path: Path):
        """Processes an individual resume within bounded concurrency."""
        async with self.semaphore:
            # 1. Parse file
            parsed: ParsedResume = await asyncio.to_thread(parse_resume_file, file_path)

            if parsed.is_malformed:
                return "failed", {
                    "file_name": file_path.name,
                    "error": parsed.parse_error or "Unknown parsing failure"
                }

            # 2. Hard Eligibility Filter
            eligibility: EligibilityResult = evaluate_eligibility(parsed)

            if not eligibility.eligible:
                rejected = RejectedCandidate(
                    candidate=eligibility.candidate,
                    eligible=False,
                    rejection_reasons=eligibility.rejection_reasons,
                    matched_skills=eligibility.matched_skills,
                    file_name=file_path.name
                )
                return "rejected", rejected

            # 3. GitHub Enrichment (Only for eligible candidates)
            github_signal = await fetch_github_signals(parsed.github_username)

            # 4. Scoring Engine
            scored_candidate = await self.scorer.score_candidate(parsed, github_signal)
            scored_candidate.file_name = file_path.name

            return "eligible", scored_candidate

    @staticmethod
    def export_json(report: ScreeningReport, output_path: Path) -> None:
        """Export screening results to pretty JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Format list conforming to assignment specification
        # Section 7: Minimum final outputs include:
        # [ { "rank": 1, "candidate_name": "...", "eligible": true, "total_score": 86, ... } ]
        # Along with rejected candidates and summary
        export_data = {
            "batch_summary": report.summary.model_dump(),
            "ranked_shortlist": [c.model_dump() for c in report.ranked_candidates],
            "rejected_candidates": [r.model_dump() for r in report.rejected_candidates],
            "failed_files": report.failed_files
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

    @staticmethod
    def export_csv(report: ScreeningReport, output_path: Path) -> None:
        """Export ranked eligible candidates to CSV."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Rank", "Candidate Name", "Total Score", "AI Project Depth",
                "Python Backend", "Cloud Fullstack", "GitHub Score",
                "Engineering Depth", "Matched Skills", "GitHub Summary", "Project Summary"
            ])
            for c in report.ranked_candidates:
                writer.writerow([
                    c.rank,
                    c.candidate_name,
                    c.total_score,
                    c.score_breakdown.ai_project_depth,
                    c.score_breakdown.python_backend,
                    c.score_breakdown.cloud_fullstack,
                    c.score_breakdown.github,
                    c.score_breakdown.engineering_depth,
                    ", ".join(c.matched_skills),
                    c.github_summary,
                    c.project_summary
                ])
