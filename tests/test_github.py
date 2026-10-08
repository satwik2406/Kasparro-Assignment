"""
Unit tests for GitHub Enrichment.
"""

import pytest
from unittest.mock import patch, AsyncMock
from src.enrichment.github import fetch_github_signals, _GITHUB_CACHE


@pytest.mark.asyncio
async def test_missing_github_profile():
    """Missing or None username returns skipped signal with 0 score."""
    signal = await fetch_github_signals(None)
    assert signal.profile_found is False
    assert signal.total_github_score == 0
    assert signal.enrichment_status == "skipped"


@pytest.mark.asyncio
async def test_github_caching():
    """Verify that cached profile results are retrieved directly from memory."""
    username = "testuser_cached"
    # Prepopulate cache
    from src.models import GitHubSignal
    mock_signal = GitHubSignal(
        username=username,
        profile_found=True,
        total_github_score=7,
        summary="Cached profile test",
        enrichment_status="success"
    )
    _GITHUB_CACHE[username] = mock_signal

    res = await fetch_github_signals(username)
    assert res.total_github_score == 7
    assert res.summary == "Cached profile test"


@pytest.mark.asyncio
async def test_graceful_failure_on_exception():
    """Verify network exceptions are caught and never crash the screener."""
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        signal = await fetch_github_signals("some_random_user_99999")
        assert signal.profile_found is False
        assert signal.total_github_score == 0
        assert signal.enrichment_status == "failed"
