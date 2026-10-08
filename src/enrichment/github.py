"""
GitHub profile enrichment module.
Fetches public profile, repository, and event data asynchronously.
Capped at 10 points. Graceful degradation on 404, rate limits, or network errors.
"""

import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from src.config import settings
from src.models import GitHubSignal


# In-memory enrichment cache (username -> GitHubSignal)
_GITHUB_CACHE: Dict[str, GitHubSignal] = {}

AI_KEYWORDS = {"ai", "llm", "rag", "agent", "langchain", "langgraph", "fastapi", "python", "pytorch", "vector"}


async def fetch_github_signals(username: Optional[str]) -> GitHubSignal:
    """
    Fetch public GitHub activity and repository statistics.
    Never raises an uncaught exception; returns default signal on error.
    """
    if not username:
        return GitHubSignal(
            username=None,
            profile_found=False,
            summary="No GitHub profile provided on resume.",
            enrichment_status="skipped"
        )

    clean_user = username.strip().lower()
    if clean_user in _GITHUB_CACHE:
        return _GITHUB_CACHE[clean_user]

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Resume-Screener/1.0"
    }
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    timeout = httpx.Timeout(settings.request_timeout_seconds)

    try:
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            # 1. Fetch user base info
            user_resp = await client.get(f"https://api.github.com/users/{clean_user}")
            if user_resp.status_code == 404:
                signal = GitHubSignal(
                    username=clean_user,
                    profile_found=False,
                    summary=f"GitHub profile @{clean_user} was not found (404).",
                    enrichment_status="not_found"
                )
                _GITHUB_CACHE[clean_user] = signal
                return signal
            elif user_resp.status_code in [403, 429]:
                signal = GitHubSignal(
                    username=clean_user,
                    profile_found=False,
                    summary="GitHub API rate limit reached; enrichment skipped gracefully.",
                    enrichment_status="rate_limited"
                )
                _GITHUB_CACHE[clean_user] = signal
                return signal
            elif user_resp.status_code != 200:
                signal = GitHubSignal(
                    username=clean_user,
                    profile_found=False,
                    summary=f"GitHub API returned HTTP {user_resp.status_code}; enrichment skipped.",
                    enrichment_status="failed"
                )
                _GITHUB_CACHE[clean_user] = signal
                return signal

            user_data = user_resp.json()
            public_repos_count = user_data.get("public_repos", 0)

            # 2. Fetch recent repositories
            repos_resp = await client.get(
                f"https://api.github.com/users/{clean_user}/repos?per_page=30&sort=updated"
            )
            maintained_relevant_count = 0
            if repos_resp.status_code == 200:
                repos = repos_resp.json()
                for repo in repos:
                    # Ignore external forks to reward maintained / owned repos
                    if repo.get("fork", False):
                        continue
                    lang = (repo.get("language") or "").lower()
                    desc = (repo.get("description") or "").lower()
                    topics = [t.lower() for t in repo.get("topics", [])]

                    is_python = lang == "python"
                    has_ai_topics = any(k in desc or k in topics for k in AI_KEYWORDS)

                    if is_python or has_ai_topics:
                        maintained_relevant_count += 1

            # 3. Fetch recent events (pushes, pull requests, releases)
            events_resp = await client.get(
                f"https://api.github.com/users/{clean_user}/events?per_page=30"
            )
            recent_events_count = 0
            if events_resp.status_code == 200:
                events = events_resp.json()
                cutoff = datetime.now(timezone.utc) - timedelta(days=90)
                for ev in events:
                    created_str = ev.get("created_at")
                    if created_str:
                        try:
                            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                            if created_dt >= cutoff:
                                recent_events_count += 1
                        except Exception:
                            continue

            # Calculate scores (0-5 for activity, 0-5 for relevant maintained repos)
            # Recent Activity:
            if recent_events_count >= 10:
                recent_activity_score = 5
            elif recent_events_count >= 5:
                recent_activity_score = 4
            elif recent_events_count >= 2:
                recent_activity_score = 2
            elif recent_events_count >= 1:
                recent_activity_score = 1
            else:
                recent_activity_score = 0

            # Maintained Relevant Repos:
            if maintained_relevant_count >= 4:
                relevant_repo_score = 5
            elif maintained_relevant_count >= 2:
                relevant_repo_score = 4
            elif maintained_relevant_count >= 1:
                relevant_repo_score = 2
            else:
                relevant_repo_score = 1 if public_repos_count > 0 else 0

            total_github_score = min(10, recent_activity_score + relevant_repo_score)

            summary_parts = []
            if recent_events_count > 0:
                summary_parts.append(f"Recently active ({recent_events_count} events in last 90 days)")
            else:
                summary_parts.append("Low recent public commit activity")

            if maintained_relevant_count > 0:
                summary_parts.append(f"{maintained_relevant_count} maintained Python/AI repositories")
            else:
                summary_parts.append(f"{public_repos_count} public repositories")

            signal = GitHubSignal(
                username=clean_user,
                profile_found=True,
                public_repos_count=public_repos_count,
                maintained_relevant_repos=maintained_relevant_count,
                recent_events_count=recent_events_count,
                recent_activity_score=recent_activity_score,
                relevant_repo_score=relevant_repo_score,
                total_github_score=total_github_score,
                summary="; ".join(summary_parts) + ".",
                enrichment_status="success"
            )
            _GITHUB_CACHE[clean_user] = signal
            return signal

    except (httpx.TimeoutException, httpx.RequestError) as e:
        signal = GitHubSignal(
            username=clean_user,
            profile_found=False,
            summary=f"GitHub network check timed out or failed ({type(e).__name__}); continued screening.",
            enrichment_status="failed"
        )
        _GITHUB_CACHE[clean_user] = signal
        return signal
    except Exception as e:
        signal = GitHubSignal(
            username=clean_user,
            profile_found=False,
            summary=f"GitHub check error: {str(e)}.",
            enrichment_status="failed"
        )
        _GITHUB_CACHE[clean_user] = signal
        return signal
