"""
tests/test_star_history.py
Unit tests for gitlytics/core.py::fetch_star_history.
All GitHub API calls are mocked so these run offline.
"""
import pytest
from unittest.mock import patch, MagicMock

from gitlytics.core import (
    fetch_star_history,
    GitHubRateLimitError,
    StarHistoryFetchError,
)


def _meta_response(stargazers_count: int, status: int = 200):
    """Build a mock GitHub repo metadata response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"stargazers_count": stargazers_count}
    return resp


def _stargazer_page(starred_at_list, status: int = 200):
    """Build a mock GitHub stargazers page response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = [
        {"starred_at": ts, "user": {"login": f"user{i}"}}
        for i, ts in enumerate(starred_at_list)
    ]
    return resp


class TestFetchStarHistoryValidation:
    def test_empty_owner_raises_value_error(self):
        # Bad input must not hit the network — fail fast with ValueError.
        with pytest.raises(ValueError, match="requires owner"):
            fetch_star_history("", "repo")

    def test_empty_repo_raises_value_error(self):
        with pytest.raises(ValueError, match="requires owner"):
            fetch_star_history("owner", "")

    def test_slash_in_repo_raises_value_error(self):
        # A repo name like 'a/b/c' is malformed — refuse before the API call.
        with pytest.raises(ValueError, match="no '/'"):
            fetch_star_history("owner", "a/b/c")


class TestFetchStarHistoryErrors:
    @patch("gitlytics.core.requests.get")
    def test_429_metadata_raises_github_rate_limit_error(self, mock_get):
        # The metadata call hits the rate limit — must raise the specific
        # GitHubRateLimitError class, not a generic Exception.
        mock_get.return_value = _meta_response(0, status=429)
        with pytest.raises(GitHubRateLimitError, match="rate limit"):
            fetch_star_history("owner", "repo")

    @patch("gitlytics.core.requests.get")
    def test_403_metadata_raises_github_rate_limit_error(self, mock_get):
        # 403 with rate-limit semantics must also surface as the rate-limit class.
        mock_get.return_value = _meta_response(0, status=403)
        with pytest.raises(GitHubRateLimitError, match="rate limit"):
            fetch_star_history("owner", "repo")

    @patch("gitlytics.core.requests.get")
    def test_500_metadata_raises_star_history_fetch_error(self, mock_get):
        # 500 is a server error, not a rate limit — must raise StarHistoryFetchError.
        mock_get.return_value = _meta_response(0, status=500)
        with pytest.raises(StarHistoryFetchError, match="metadata"):
            fetch_star_history("owner", "repo")

    @patch("gitlytics.core.requests.get")
    def test_zero_stars_returns_single_today_point(self, mock_get):
        # A repo with zero stars returns a single point dated today with total=0.
        mock_get.return_value = _meta_response(0, status=200)
        points = fetch_star_history("owner", "repo")
        assert len(points) == 1
        assert points[0]["total"] == 0
        # Should NOT have made a second API call for the stargazers endpoint.
        assert mock_get.call_count == 1


class TestFetchStarHistorySmallRepo:
    """Repos with <= 200 stars use the fine-grained per-page walk."""

    @patch("gitlytics.core.requests.get")
    def test_small_repo_walks_per_star(self, mock_get):
        # 5-star repo: 5 stargazers to walk. Use the small_per_page of 30 so
        # all 5 land in a single page-1 response.
        meta = _meta_response(5, status=200)
        page = _stargazer_page(
            [
                "2024-01-01T00:00:00Z",
                "2024-01-02T00:00:00Z",
                "2024-01-03T00:00:00Z",
                "2024-01-04T00:00:00Z",
                "2024-01-05T00:00:00Z",
            ]
        )
        # Side effects: first call returns metadata, second returns the stargazer page.
        mock_get.side_effect = [meta, page]
        points = fetch_star_history("owner", "repo")
        # The function should return a monotonically-increasing cumulative timeline
        # with today's total equal to the live count (5).
        assert points, "Expected at least one point"
        assert points[-1]["total"] == 5
        # Cumulative totals must never decrease across dates.
        totals = [p["total"] for p in points]
        assert totals == sorted(totals)
        # Network: metadata + 1 stargazer page.
        assert mock_get.call_count == 2


class TestFetchStarHistoryLargeRepo:
    """Repos with > 200 stars use the 10-page sampling strategy."""

    @patch("gitlytics.core.requests.get")
    def test_large_repo_samples_ten_pages(self, mock_get):
        # 5000-star repo: should pick 10 evenly-spaced positions across the first
        # 422 pages (GitHub's pagination ceiling).
        meta = _meta_response(5000, status=200)
        # Each sampled page returns 100 items with starred_at timestamps.
        star_date = "2020-06-15T00:00:00Z"
        page = _stargazer_page([star_date] * 100)
        # 1 metadata call + 10 page calls.
        mock_get.side_effect = [meta] + [page] * 10
        points = fetch_star_history("owner", "repo")
        # The total must monotonically increase to today's 5000.
        assert points[-1]["total"] == 5000
        # Network calls: metadata + 10 stargazer pages.
        assert mock_get.call_count == 11

    @patch("gitlytics.core.requests.get")
    def test_large_repo_429_on_stargazer_page_raises_rate_limit(self, mock_get):
        # If the metadata succeeds but a stargazer page hits 429,
        # the function must raise GitHubRateLimitError (not a generic Exception).
        meta = _meta_response(5000, status=200)
        rate_limited = _meta_response(0, status=429)
        mock_get.side_effect = [meta, rate_limited]
        with pytest.raises(GitHubRateLimitError, match="rate limit"):
            fetch_star_history("owner", "repo")


class TestFetchStarHistoryTokenOptional:
    @patch("gitlytics.core.requests.get")
    def test_no_token_still_works_for_public_repos(self, mock_get):
        # Public reads do not need auth. The function should pass through
        # without raising even when token=None.
        meta = _meta_response(0, status=200)
        mock_get.return_value = meta
        points = fetch_star_history("owner", "repo", token=None)
        assert points == [{"date": points[0]["date"], "total": 0}]