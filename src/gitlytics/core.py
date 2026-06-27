# Copyright (c) 2026 Ameya Sanjay Chopade
# SPDX-License-Identifier: Apache-2.0
# Licensed under Apache-2.0.
# See LICENSE.md for full terms.
"""
gitlytics/core.py
Handles fetching traffic and deep metadata from the GitHub API.
"""
import json
import logging

import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

BASE = "https://api.github.com"
# Single source of truth for the GitHub media-type + API version headers.
_GITHUB_BASE_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
_PUBLIC_HEADERS = dict(_GITHUB_BASE_HEADERS)
_MAX_RELEASE_PAGES = 10      # hard cap when walking /releases
_MAX_PR_PAGES = 10           # hard cap when walking /pulls
_MAX_COMMIT_PAGES = 50       # hard cap when counting /commits (50 * 100 = 5000)
_PER_PAGE = 100              # request size for paginated endpoints


class GitHubRateLimitError(Exception):
    """Raised when GitHub responds with 403/429 (rate limit or abuse guard)."""


class StarHistoryFetchError(Exception):
    """Raised for non-rate-limit star-history failures (network, parse, validation)."""


def make_headers(token: str) -> dict:
    # Auth headers for authenticated API calls
    return {
        "Authorization": f"Bearer {token}",
        **_GITHUB_BASE_HEADERS,
    }


def validate_token(token: str) -> tuple[bool, str]:
    # Try to reach the GitHub /user endpoint with the given token
    try:
        r = requests.get(f"{BASE}/user", headers=make_headers(token), timeout=10)
    except requests.exceptions.ConnectionError:
        return False, "No internet connection."
    except Exception as e:
        return False, str(e)

    if r.status_code == 200:
        data = r.json()
        return True, data.get("login", "")
    if r.status_code == 401:
        return False, "Invalid token — authentication failed (401 Unauthorized)."
    if r.status_code == 403:
        return False, "Token has insufficient permissions (403 Forbidden)."
    return False, f"GitHub returned HTTP {r.status_code}."


def get_user_profile(token: str) -> dict:
    """Returns the authenticated user's full profile."""
    try:
        r = requests.get(f"{BASE}/user", headers=make_headers(token), timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "login": data.get("login", ""),
                "name": data.get("name") or data.get("login", ""),
                "avatar_url": data.get("avatar_url", ""),
                "bio": data.get("bio"),
                "location": data.get("location"),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
            }
    except Exception as exc:
        logger.warning(f"Could not fetch user profile: {exc}")
    return {"login": "", "name": "", "avatar_url": "", "followers": 0, "following": 0}


def get_public_user(username: str) -> dict:
    """Fetches a public GitHub user profile — no PAT required."""
    try:
        r = requests.get(f"{BASE}/users/{username}", headers=_PUBLIC_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "login": data.get("login", ""),
                "name": data.get("name") or data.get("login", ""),
                "avatar_url": data.get("avatar_url", ""),
                "bio": data.get("bio"),
                "location": data.get("location"),
                "blog": data.get("blog"),
                "twitter_username": data.get("twitter_username"),
                "html_url": data.get("html_url", ""),
                "followers": data.get("followers", 0),
                "following": data.get("following", 0),
                "public_repos": data.get("public_repos", 0),
                "created_at": data.get("created_at", ""),
            }
        if r.status_code == 404:
            raise ValueError(f"User '{username}' not found.")
        # 5xx and other unexpected codes — log a warning and return a stub so the
        # caller (the API endpoint) can return a 502 without leaking the failure.
        logger.warning(f"Failed to fetch user {username}: HTTP {r.status_code}")
    except ValueError:
        # Re-raise user-not-found as-is.
        raise
    except Exception as exc:
        logger.warning(f"Could not fetch public user profile: {exc}")
    return {"login": username, "name": username, "avatar_url": ""}


def _normalise_repo(repo: dict) -> dict:
    # Extract only the fields the dashboard needs from a raw GitHub repo object
    return {
        "name": repo.get("name", ""),
        "full_name": repo.get("full_name", ""),
        "description": repo.get("description"),
        "html_url": repo.get("html_url", ""),
        "fork": repo.get("fork", False),
        "stargazers_count": repo.get("stargazers_count", 0),
        "forks_count": repo.get("forks_count", 0),
        "watchers_count": repo.get("watchers_count", 0),
        "language": repo.get("language"),
        "open_issues_count": repo.get("open_issues_count", 0),
        "topics": repo.get("topics", []),
        "pushed_at": repo.get("pushed_at", ""),
        "created_at": repo.get("created_at", ""),
        "default_branch": repo.get("default_branch", "main"),
    }


def _fetch_public_repos_by_updated(username: str, per_page: int) -> list:
    # Call 1 of 2: most-recently-updated repos (catches active new projects)
    try:
        r = requests.get(
            f"{BASE}/users/{username}/repos",
            headers=_PUBLIC_HEADERS,
            params={"per_page": per_page, "page": 1, "sort": "updated", "type": "public"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        batch = r.json()
        return [_normalise_repo(repo) for repo in batch] if isinstance(batch, list) else []
    except Exception as exc:
        logger.warning(f"Could not fetch recent repos for {username}: {exc}")
        return []


def _fetch_public_repos_by_stars(username: str, per_page: int) -> list:
    # Call 2 of 2: top-starred repos via Search API (catches famous older projects)
    try:
        r = requests.get(
            f"{BASE}/search/repositories",
            headers=_PUBLIC_HEADERS,
            params={"q": f"user:{username}", "sort": "stars", "order": "desc", "per_page": per_page},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        if not isinstance(data, dict) or "items" not in data:
            return []
        return [_normalise_repo(repo) for repo in data["items"]]
    except Exception as exc:
        logger.warning(f"Could not fetch starred repos for {username}: {exc}")
        return []


def get_public_repos(username: str, max_repos: int = 50) -> list:
    """
    Fetches up to max_repos best public repos for a username using two calls:
      1. Most recently updated (catches active projects)
      2. Most starred via Search API (catches famous older projects)
    The two lists are merged, deduplicated, sorted by stars, and capped at max_repos.
    """
    # Don't request more than the caller actually wants.
    per_page = min(50, max_repos) if max_repos > 0 else 50
    recent = _fetch_public_repos_by_updated(username, per_page=per_page)
    starred = _fetch_public_repos_by_stars(username, per_page=per_page)

    seen: set = set()
    merged = []
    for repo in recent + starred:
        key = repo.get("full_name", "")
        if key and key not in seen:
            seen.add(key)
            merged.append(repo)

    merged.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
    return merged[:max_repos]


def _safe_get(url: str, headers: dict, params: dict = None) -> tuple:
    """Wraps requests.get with error handling and returns (data, status_code)."""
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # GitHub occasionally returns 200 with a soft-error body. Any dict that
            # contains a "message" field is treated as a soft error (caller decides
            # what to do with status 200 + empty body).
            if isinstance(data, dict) and data.get("message"):
                logger.warning(f"GitHub soft-error for {url}: {data['message']}")
                return {}, r.status_code
            return data, 200
        if r.status_code == 429:
            logger.warning(f"GitHub API rate limit hit (429) for {url}.")
        elif r.status_code == 403:
            logger.warning(f"Access denied (403) for {url}.")
        elif r.status_code != 404:
            logger.warning(f"Unexpected HTTP {r.status_code} for {url}.")
        return {}, r.status_code
    except requests.exceptions.Timeout:
        logger.warning(f"Request timed out for {url}.")
        return {}, -1
    except Exception as exc:
        logger.warning(f"Request failed for {url}: {exc}")
        return {}, -1


def _walk_paginated_count(url: str, headers: dict, params: dict, max_pages: int) -> int:
    """
    Count items across pages. Returns the total count, capped at max_pages * per_page.
    The GitHub REST API for /pulls and /releases does not return a total_count,
    so we have to walk pages.
    """
    total = 0
    per_page = int(params.get("per_page", _PER_PAGE)) if params else _PER_PAGE
    page_params = dict(params or {})
    page_params["per_page"] = per_page
    for page in range(1, max_pages + 1):
        page_params["page"] = page
        data, status = _safe_get(url, headers, page_params)
        if status != 200 or not isinstance(data, list) or not data:
            break
        total += len(data)
        if len(data) < per_page:
            break
    return total


def get_deep_repo_stats(token: str, full_name: str) -> dict:
    """Fetches commit activity, open PRs, releases, and community health for one repo."""
    h = make_headers(token)
    stats = {
        "total_commits": None,
        "open_prs": None,
        "total_releases": None,
        "last_release_at": None,
        "has_readme": None,
        "has_license": None,
        "has_contributing": None,
        "has_code_of_conduct": None,
    }

    # Commit activity — GitHub computes this async and returns 202 when not ready.
    # NOTE: stats/commit_activity only reports the trailing 52-week window, so for
    # repos where the user expects to see lifetime history we count via
    # /repos/{full_name}/commits?per_page=100 and walk pages. GitHub hard-caps
    # /commits at ~1000 results on a single unauthenticated/traffic endpoint, so
    # the lifetime count returned here is the lifetime visible to the API.
    ca_url = f"{BASE}/repos/{full_name}/stats/commit_activity"
    ca_data, status = _safe_get(ca_url, h)
    if status == 202:
        logger.info(f"Commit activity not ready yet (202) for {full_name}; will populate on next fetch.")
    if isinstance(ca_data, list) and ca_data:
        stats["total_commits"] = sum(week.get("total", 0) for week in ca_data)
    else:
        # Fall back to a lifetime count when stats/commit_activity is empty or
        # not yet computed (202 / empty list). Walking /commits is slower but
        # always returns the real lifetime history for repos under ~10k commits.
        commits_url = f"{BASE}/repos/{full_name}/commits"
        try:
            stats["total_commits"] = _walk_paginated_count(
                commits_url, h, {"per_page": _PER_PAGE}, _MAX_COMMIT_PAGES
            )
        except Exception as exc:
            logger.warning(f"Could not fetch commit count for {full_name}: {exc}")

    # Open PRs — walk pages because GitHub's /pulls endpoint doesn't return a total.
    pr_url = f"{BASE}/repos/{full_name}/pulls"
    try:
        stats["open_prs"] = _walk_paginated_count(pr_url, h, {"state": "open"}, _MAX_PR_PAGES)
    except Exception as exc:
        logger.warning(f"Could not fetch open PRs for {full_name}: {exc}")

    # Community health profile — README, license, contributing, CoC
    cp_data, _ = _safe_get(f"{BASE}/repos/{full_name}/community/profile", h)
    if isinstance(cp_data, dict) and "files" in cp_data:
        files = cp_data.get("files", {})
        stats["has_readme"] = bool(files.get("readme"))
        stats["has_license"] = bool(files.get("license"))
        stats["has_contributing"] = bool(files.get("contributing"))
        stats["has_code_of_conduct"] = bool(files.get("code_of_conduct"))

    # Releases — walk pages to get the real total, then read the latest's date from
    # the first page (GitHub returns releases sorted newest-first, so page=1 has it).
    try:
        rel_url = f"{BASE}/repos/{full_name}/releases"
        first_page, status = _safe_get(rel_url, h, {"per_page": _PER_PAGE, "page": 1})
        if status == 200 and isinstance(first_page, list):
            stats["total_releases"] = _walk_paginated_count(
                rel_url, h, {"per_page": _PER_PAGE}, _MAX_RELEASE_PAGES
            )
            if first_page:
                latest = first_page[0]
                stats["last_release_at"] = latest.get("published_at") or latest.get("created_at")
    except Exception as exc:
        logger.warning(f"Could not fetch releases for {full_name}: {exc}")

    return stats


def fetch_deep_stats_for_top(token: str, repos_with_views: list, top_n: int = 20) -> dict:
    """Runs get_deep_repo_stats concurrently for the top N repos by views."""
    # Sort by total views descending and take the top slice
    ranked = sorted(repos_with_views, key=lambda x: x.get("total_views", 0), reverse=True)
    top = ranked[:top_n]
    results = {}

    def fetch_one(full_name: str):
        return full_name, get_deep_repo_stats(token, full_name)

    # 5 workers keeps us well inside GitHub's abuse rate limit. The default
    # `get_deep_repo_stats` issues 3 requests per repo (commit activity, PRs,
    # releases) plus a community profile — so 5 workers = 20 concurrent calls.
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_one, r["repository"]): r["repository"] for r in top}
        for future in as_completed(futures):
            try:
                name, stats = future.result()
                results[name] = stats
            except Exception as exc:
                logger.warning(f"Deep stats fetch failed for {futures[future]}: {exc}")

    return results


def get_all_repos(token: str) -> list[dict]:
    # Page through every repo the token can see
    headers = make_headers(token)
    repos, page = [], 1
    seen = set()
    while True:
        data, _ = _safe_get(f"{BASE}/user/repos", headers, {"per_page": _PER_PAGE, "page": page, "type": "all"})
        # L-2: check isinstance before truthiness to avoid dict falsy short-circuit
        if not isinstance(data, list) or len(data) == 0:
            break
        for repo in data:
            fname = repo.get("full_name")
            if fname and fname not in seen:
                seen.add(fname)
                repos.append(repo)
        # Stop when the page is short — this is the natural end of pagination.
        if len(data) < _PER_PAGE:
            break
        page += 1
    return repos


def get_single_repo(token: str, full_name: str) -> dict:
    # Fetch metadata for one specific repo
    headers = make_headers(token)
    data, status = _safe_get(f"{BASE}/repos/{full_name}", headers)
    if not data or "name" not in data:
        raise ValueError(
            f"Repository '{full_name}' not found or token lacks access "
            f"(HTTP {status})."
        )
    return data


def _star_headers(token: str | None) -> dict:
    # Headers for the stargazers endpoint — needs the star+json media type
    # so each item carries `starred_at`. Token is optional for public reads.
    # Merge order matters: star+json must land AFTER the base headers so it
    # overrides the default Accept (otherwise GitHub returns bare user objects).
    h = {
        **_GITHUB_BASE_HEADERS,
        "Accept": "application/vnd.github.star+json",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_star_history(owner: str, repo: str, token: str | None = None) -> list[dict]:
    # Returns list of {date, total} cumulative points. No on-disk cache — the
    # library always reads live from GitHub; the browser (IndexedDB via
    # TanStack) and the Vercel CDN cache handle persistence upstream.
    if not owner or not repo or "/" in repo:
        raise ValueError("fetch_star_history requires owner and repo (no '/' in repo).")

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # Live fetch — pull total star count from the repo metadata endpoint.
    meta, status = _safe_get(f"{BASE}/repos/{owner}/{repo}", _star_headers(token))
    if status in (403, 429):
        # GitHub's rate-limit guard returns 403 with a 'rate limit' message in body.
        raise GitHubRateLimitError("GitHub rate limit reached, try again later")
    if status != 200 or not isinstance(meta, dict):
        raise StarHistoryFetchError(f"Failed to fetch repo metadata (HTTP {status})")
    total_stars = int(meta.get("stargazers_count", 0) or 0)
    if total_stars <= 0:
        return [{"date": today_str, "total": 0}]

    headers = _star_headers(token)
    per_page = _PER_PAGE
    points: list[dict] = []
    # Choose strategy based on repo size so small repos get a real
    # datewise timeline (every individual star) while large repos use
    # sampling to stay under rate limits.
    SMALL_THRESHOLD = 200
    if total_stars <= SMALL_THRESHOLD:
        # Walk every page at smaller page size for finer granularity.
        small_per_page = 30
        positions = list(range(1, total_stars + 1))
        # Use the small page size for these requests.
        per_page = small_per_page
        small_by_page: dict[int, list[int]] = {}
        for pos in positions:
            p = (pos - 1) // small_per_page + 1
            small_by_page.setdefault(p, []).append(pos)
        for p, poses in small_by_page.items():
            try:
                r = requests.get(
                    f"{BASE}/repos/{owner}/{repo}/stargazers",
                    headers=headers,
                    params={"page": p, "per_page": small_per_page},
                    timeout=10,
                )
            except Exception as exc:
                logger.warning(f"Stargazers fetch failed for {owner}/{repo} page {p}: {exc}")
                continue
            if r.status_code in (403, 429):
                raise GitHubRateLimitError("GitHub rate limit reached, try again later")
            if r.status_code != 200:
                logger.warning(f"Stargazers page {p} returned HTTP {r.status_code}")
                continue
            items = r.json()
            if not isinstance(items, list):
                continue
            for pos in poses:
                offset = (pos - 1) % small_per_page
                if offset >= len(items):
                    continue
                item = items[offset]
                if not isinstance(item, dict):
                    continue
                starred_at = item.get("starred_at")
                if not starred_at:
                    continue
                points.append({"date": str(starred_at)[:10], "total": pos})
    else:
        # Pick 10 evenly-spaced individual stars. GitHub only keeps the last
        # ~420 pages of stargazers even for huge repos so we cap the page
        # range to avoid 422s on the upper bound.
        max_pages = 422
        max_position = min(total_stars, max_pages * per_page)
        sample_count = 10
        if max_position == 1:
            sampled = [1]
        else:
            step = (max_position - 1) / (sample_count - 1)
            sampled = sorted({max(1, min(max_position, round(1 + i * step))) for i in range(sample_count)})
        # Group positions by page so each page is requested at most once.
        by_page: dict[int, list[int]] = {}
        for pos in sampled:
            p = (pos - 1) // per_page + 1
            by_page.setdefault(p, []).append(pos)
        for p, poses in by_page.items():
            try:
                r = requests.get(
                    f"{BASE}/repos/{owner}/{repo}/stargazers",
                    headers=headers,
                    params={"page": p, "per_page": per_page},
                    timeout=10,
                )
            except Exception as exc:
                logger.warning(f"Stargazers fetch failed for {owner}/{repo} page {p}: {exc}")
                continue
            if r.status_code in (403, 429):
                raise GitHubRateLimitError("GitHub rate limit reached, try again later")
            if r.status_code != 200:
                logger.warning(f"Stargazers page {p} returned HTTP {r.status_code}")
                continue
            items = r.json()
            if not isinstance(items, list):
                continue
            for pos in poses:
                offset = (pos - 1) % per_page
                if offset >= len(items):
                    continue
                item = items[offset]
                if not isinstance(item, dict):
                    continue
                starred_at = item.get("starred_at")
                if not starred_at:
                    continue
                points.append({"date": str(starred_at)[:10], "total": pos})

    # Build a per-day cumulative timeline. Each entry means "by end of <date>,
    # this repo had <total> stars". Today always equals the live stargazers
    # count so the chart's right edge is the current count.
    per_day_max: dict[str, int] = {}
    for p in points:
        d = p["date"]
        per_day_max[d] = max(per_day_max.get(d, 0), int(p["total"]))
    if not per_day_max or max(per_day_max.values()) < total_stars:
        per_day_max[today_str] = total_stars

    # Convert raw "max position on this day" into a running cumulative count.
    # Stars are monotone — total can never decrease across dates.
    sorted_dates = sorted(per_day_max.keys())
    cumulative = 0
    points: list[dict] = []
    for d in sorted_dates:
        cumulative = max(cumulative, per_day_max[d])
        points.append({"date": d, "total": cumulative})
    if points and points[-1]["date"] != today_str:
        points.append({"date": today_str, "total": max(cumulative, total_stars)})
    if points and points[-1]["total"] < total_stars:
        points[-1] = {"date": today_str, "total": total_stars}

    return points


def get_repo_traffic(token: str, full_name: str, metrics: list = None) -> dict:
    # Fetch only the traffic endpoints requested in metrics
    h = make_headers(token)

    views, clones, refs, paths = {}, {}, [], []
    if metrics is None or "views" in metrics:
        views, _ = _safe_get(f"{BASE}/repos/{full_name}/traffic/views", h)
    if metrics is None or "clones" in metrics:
        clones, _ = _safe_get(f"{BASE}/repos/{full_name}/traffic/clones", h)
    if metrics is None or "referrers" in metrics:
        refs, _ = _safe_get(f"{BASE}/repos/{full_name}/traffic/popular/referrers", h)
    if metrics is None or "paths" in metrics:
        paths, _ = _safe_get(f"{BASE}/repos/{full_name}/traffic/popular/paths", h)

    return {
        "views": views if isinstance(views, dict) else {},
        "clones": clones if isinstance(clones, dict) else {},
        "referrers": refs if isinstance(refs, list) else [],
        "paths": paths if isinstance(paths, list) else [],
    }


def pad_traffic_data(traffic: dict) -> list[dict]:
    # GitHub only returns days with activity — fill gaps with zeros
    views_list = traffic.get("views", {}).get("views", []) or []
    clones_list = traffic.get("clones", {}).get("clones", []) or []

    latest_date_str = None
    for item in views_list + clones_list:
        ts = item.get("timestamp", "")
        date_str = ts[:10] if isinstance(ts, str) else ""
        if not date_str:
            continue
        if latest_date_str is None or date_str > latest_date_str:
            latest_date_str = date_str

    if latest_date_str:
        try:
            end_date = datetime.strptime(latest_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Could not parse traffic date {latest_date_str!r}; falling back to today.")
            end_date = datetime.now(timezone.utc)
    else:
        end_date = datetime.now(timezone.utc)

    dates = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    # Guard against rows missing a timestamp (rare but possible on partial responses).
    views_map = {v.get("timestamp", "")[:10]: v for v in views_list if isinstance(v, dict) and v.get("timestamp")}
    clones_map = {c.get("timestamp", "")[:10]: c for c in clones_list if isinstance(c, dict) and c.get("timestamp")}

    padded = []
    for d in dates:
        v = views_map.get(d, {}) or {}
        c = clones_map.get(d, {}) or {}
        padded.append({
            "date": d,
            "views": int(v.get("count", 0) or 0),
            "unique_visitors": int(v.get("uniques", 0) or 0),
            "clones": int(c.get("count", 0) or 0),
            "unique_cloners": int(c.get("uniques", 0) or 0)
        })
    return padded


def build_tidy_rows(repo: dict, traffic: dict, metrics: list = None) -> list[dict]:
    # One CSV row per calendar day — repo metadata repeated on every row
    padded = pad_traffic_data(traffic)
    refs = traffic.get("referrers", [])
    paths = traffic.get("paths", [])

    top_ref = refs[0].get("referrer", "") if refs else ""
    top_ref_views = refs[0].get("count", 0) if refs else 0
    top_ref_uniques = refs[0].get("uniques", 0) if refs else 0
    top_path = paths[0].get("path", "") if paths else ""
    top_path_views = paths[0].get("count", 0) if paths else 0
    top_path_uniques = paths[0].get("uniques", 0) if paths else 0

    rows = []
    for day in padded:
        row = {
            "date": day["date"],
            "repository": repo["full_name"],
            "is_private": repo.get("private", False),
        }
        if metrics is None or "views" in metrics:
            row["views"] = day["views"]
            row["unique_visitors"] = day["unique_visitors"]
        if metrics is None or "clones" in metrics:
            row["clones"] = day["clones"]
            row["unique_cloners"] = day["unique_cloners"]
        if metrics is None or "stars" in metrics:
            row["stars"] = repo.get("stargazers_count", 0)
        if metrics is None or "forks" in metrics:
            row["forks"] = repo.get("forks_count", 0)

        # Repo metadata that the deep dashboard needs
        if metrics is None or "language" in metrics:
            row["language"] = repo.get("language")
        if metrics is None or "topics" in metrics:
            row["topics"] = json.dumps(repo.get("topics", []))
        if metrics is None or "watchers_count" in metrics:
            row["watchers_count"] = repo.get("watchers_count", 0)
        if metrics is None or "pushed_at" in metrics:
            row["pushed_at"] = repo.get("pushed_at", "")
        if metrics is None or "created_at" in metrics:
            row["created_at"] = repo.get("created_at", "")
        if metrics is None or "open_issues_count" in metrics:
            row["open_issues_count"] = repo.get("open_issues_count", 0)

        if metrics is None or "referrers" in metrics:
            row["top_referrer"] = top_ref
            row["top_referrer_views"] = top_ref_views
            row["top_referrer_uniques"] = top_ref_uniques
            row["_raw_referrers"] = json.dumps(refs)

        if metrics is None or "paths" in metrics:
            row["top_path"] = top_path
            row["top_path_views"] = top_path_views
            row["top_path_uniques"] = top_path_uniques
            row["_raw_paths"] = json.dumps(paths)

        rows.append(row)
    return rows


def fetch_traffic_data(token: str, repo_names=None, metrics: list = None) -> pd.DataFrame:
    # Decide whether to fetch one repo, a custom list, or all repos
    if repo_names is not None:
        if isinstance(repo_names, str):
            repo_names = [repo_names]
        # Treat an explicit empty list as "fetch nothing" rather than falling through
        # to get_all_repos (which would fetch every accessible repo).
        if len(repo_names) == 0:
            return pd.DataFrame()
        repos = [get_single_repo(token, name) for name in repo_names]
    else:
        repos = get_all_repos(token)

    all_rows = []
    for repo in repos:
        traffic = get_repo_traffic(token, repo["full_name"], metrics)
        all_rows.extend(build_tidy_rows(repo, traffic, metrics))

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()


def print_repo_table(df: pd.DataFrame):
    if df.empty:
        print("No data to display.")
        return

    # Replace NaN with empty string for clean printing (no literal "nan").
    safe_df = df.fillna("")

    repo_width = max(30, safe_df["repository"].astype(str).str.len().max() + 2)
    ref_width = max(15, safe_df["top_referrer"].astype(str).str.len().max() + 2) if "top_referrer" in safe_df.columns else 15
    header = (
        f"{'REPOSITORY':<{repo_width}} "
        f"{'VIEWS':<8} {'U.VIEWS':<8} {'CLONES':<8} {'U.CLONES':<8} "
        f"{'STARS':<8} {'FORKS':<8} {'TOP REFERRER':<{ref_width}}"
    )
    print(header)
    print("-" * len(header))

    total_account_views = 0
    total_account_uniques = 0
    total_account_clones = 0

    for repo in safe_df["repository"].unique():
        repo_df = safe_df[safe_df["repository"] == repo]
        views = int(repo_df["views"].sum()) if "views" in repo_df.columns else 0
        u_views = int(repo_df["unique_visitors"].sum()) if "unique_visitors" in repo_df.columns else 0
        clones = int(repo_df["clones"].sum()) if "clones" in repo_df.columns else 0
        u_clones = int(repo_df["unique_cloners"].sum()) if "unique_cloners" in repo_df.columns else 0
        stars = repo_df.iloc[-1]["stars"] if "stars" in repo_df.columns else 0
        forks = repo_df.iloc[-1]["forks"] if "forks" in repo_df.columns else 0
        top_ref = repo_df.iloc[-1].get("top_referrer", "") if "top_referrer" in repo_df.columns else ""

        total_account_views += views
        total_account_uniques += u_views
        total_account_clones += clones

        print(
            f"{repo:<{repo_width}} "
            f"{views:<8} {u_views:<8} {clones:<8} {u_clones:<8} "
            f"{stars:<8} {forks:<8} {str(top_ref):<{ref_width}}"
        )

    print("-" * len(header))
    print(f"Total Account Views:  {total_account_views} (Unique: {total_account_uniques})")
    print(f"Total Account Clones: {total_account_clones}")
