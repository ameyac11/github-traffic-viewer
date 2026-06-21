# Copyright (c) 2026 Ameya Sanjay Chopade
# SPDX-License-Identifier: LicenseRef-Apache-2.0-Commons-Clause
# Licensed under Apache-2.0 with the Commons Clause restriction.
# Selling, hosting, or offering this Software as a paid service is prohibited.
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
_PUBLIC_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def make_headers(token: str) -> dict:
    # Auth headers for authenticated API calls
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
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
        logger.warning(f"Failed to fetch user {username}: HTTP {r.status_code}")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
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


def _fetch_public_repos_by_updated(username: str, per_page: int = 50) -> list:
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


def _fetch_public_repos_by_stars(username: str, per_page: int = 50) -> list:
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
    recent = _fetch_public_repos_by_updated(username, per_page=50)
    starred = _fetch_public_repos_by_stars(username, per_page=50)

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
            # GitHub occasionally returns 200 with a soft-error body (M-6)
            if isinstance(data, dict) and data.get("message") in ("Not Found", "Bad credentials"):
                logger.warning(f"GitHub soft-error for {url}: {data['message']}")
                return {}, 404
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
    # total_commits here is the trailing 52-week (12-month) sum, NOT lifetime.
    ca_url = f"{BASE}/repos/{full_name}/stats/commit_activity"
    ca_data, status = _safe_get(ca_url, h)
    if status == 202:
        logger.info(f"Commit activity not ready yet (202) for {full_name}; will populate on next fetch.")
    if isinstance(ca_data, list):
        stats["total_commits"] = sum(week.get("total", 0) for week in ca_data)

    # Open PRs — read the Link header to get the real total count (M-4)
    pr_url = f"{BASE}/repos/{full_name}/pulls"
    try:
        pr_resp = requests.get(pr_url, headers=h, params={"state": "open", "per_page": 1}, timeout=10)
        if pr_resp.status_code == 200:
            link = pr_resp.headers.get("Link", "")
            if 'rel="last"' in link:
                import re as _re
                m = _re.search(r'page=(\d+)>; rel="last"', link)
                stats["open_prs"] = int(m.group(1)) if m else len(pr_resp.json())
            else:
                stats["open_prs"] = len(pr_resp.json())
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

    # Releases — count real total using Link header pagination, then get latest date
    try:
        rel_resp = requests.get(
            f"{BASE}/repos/{full_name}/releases",
            headers=h,
            params={"per_page": 1},
            timeout=10,
        )
        if rel_resp.status_code == 200:
            link = rel_resp.headers.get("Link", "")
            if 'rel="last"' in link:
                import re as _re
                m = _re.search(r'page=(\d+)>; rel="last"', link)
                stats["total_releases"] = int(m.group(1)) if m else 1
            else:
                # Only one page — count items in this page
                items = rel_resp.json()
                stats["total_releases"] = len(items) if isinstance(items, list) else 0
            # Fetch the latest release separately for its date
            latest_resp = requests.get(
                f"{BASE}/repos/{full_name}/releases/latest",
                headers=h,
                timeout=10,
            )
            if latest_resp.status_code == 200:
                latest = latest_resp.json()
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

    # 10 workers keeps us well inside GitHub's abuse rate limit
    with ThreadPoolExecutor(max_workers=10) as pool:
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
        data, _ = _safe_get(f"{BASE}/user/repos", headers, {"per_page": 100, "page": page, "type": "all"})
        # L-2: check isinstance before truthiness to avoid dict falsy short-circuit
        if not isinstance(data, list) or len(data) == 0:
            break
        for repo in data:
            fname = repo.get("full_name")
            if fname and fname not in seen:
                seen.add(fname)
                repos.append(repo)
        if len(data) < 100:
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
    views_list = traffic.get("views", {}).get("views", [])
    clones_list = traffic.get("clones", {}).get("clones", [])

    latest_date_str = None
    for item in views_list + clones_list:
        date_str = item.get("timestamp", "")[:10]  # L-1: guard missing key
        if not date_str:
            continue
        if latest_date_str is None or date_str > latest_date_str:
            latest_date_str = date_str

    if latest_date_str:
        end_date = datetime.strptime(latest_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_date = datetime.now(timezone.utc)

    dates = [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    views_map = {v["timestamp"][:10]: v for v in views_list}
    clones_map = {c["timestamp"][:10]: c for c in clones_list}

    padded = []
    for d in dates:
        v = views_map.get(d, {})
        c = clones_map.get(d, {})
        padded.append({
            "date": d,
            "views": v.get("count", 0),
            "unique_visitors": v.get("uniques", 0),
            "clones": c.get("count", 0),
            "unique_cloners": c.get("uniques", 0)
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
    if repo_names:
        if isinstance(repo_names, str):
            repo_names = [repo_names]
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

    repo_width = max(30, df["repository"].str.len().max() + 2)
    header = f"{'REPOSITORY':<{repo_width}} {'VIEWS':<8} {'U.VIEWS':<8} {'CLONES':<8} {'U.CLONES':<8} {'STARS':<8} {'FORKS':<8} {'TOP REFERRER':<15}"
    print(header)
    print("-" * len(header))

    total_account_views = 0
    total_account_uniques = 0
    total_account_clones = 0

    for repo in df["repository"].unique():
        repo_df = df[df["repository"] == repo]
        views = repo_df["views"].sum()
        u_views = repo_df["unique_visitors"].sum()
        clones = repo_df["clones"].sum()
        u_clones = repo_df["unique_cloners"].sum()
        stars = repo_df.iloc[-1]["stars"]
        forks = repo_df.iloc[-1]["forks"]
        top_ref = repo_df.iloc[-1]["top_referrer"]

        total_account_views += views
        total_account_uniques += u_views
        total_account_clones += clones

        print(f"{repo:<{repo_width}} {views:<8} {u_views:<8} {clones:<8} {u_clones:<8} {stars:<8} {forks:<8} {top_ref:<15}")

    print("-" * len(header))
    print(f"Total Account Views:  {total_account_views} (Unique: {total_account_uniques})")
    print(f"Total Account Clones: {total_account_clones}")
