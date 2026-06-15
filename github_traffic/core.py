"""
github_traffic_fetch.py -> core.py
All GitHub API logic lives here.
"""
# This handles fetching all the raw traffic data directly from the GitHub API.

import io
import csv
import os
import sys
import requests
import pandas as pd
from datetime import datetime, timezone

# GitHub API base URL
BASE = "https://api.github.com"

# Today's date for default CSV name
DEFAULT_CSV = f"github_traffic_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"


# ── Auth ──────────────────────────────────────────────────────────────────────

def make_headers(token: str) -> dict:
    # Standard GitHub API headers
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def validate_token(token: str) -> tuple[bool, str, str, str]:
    # Check token and return user info
    try:
        r = requests.get(f"{BASE}/user", headers=make_headers(token), timeout=10)
    except requests.exceptions.ConnectionError:
        return False, "No internet connection.", "", ""
    except Exception as e:
        return False, str(e), "", ""

    if r.status_code == 200:
        data = r.json()
        return True, data.get("login", ""), data.get("avatar_url", ""), data.get("name", "")
    if r.status_code == 401:
        return False, "Invalid token — authentication failed.", "", ""
    if r.status_code == 403:
        return False, "Token has insufficient permissions.", "", ""
    return False, f"GitHub returned HTTP {r.status_code}.", "", ""


# ── Fetching repos ────────────────────────────────────────────────────────────

def _safe_get(url: str, headers: dict, params: dict = None):
    # Fetch JSON, return empty on error
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def get_all_repos(token: str) -> list[dict]:
    # Page through all user repos
    headers = make_headers(token)
    repos, page = [], 1
    while True:
        data = _safe_get(f"{BASE}/user/repos", headers, {"per_page": 100, "page": page, "type": "all"})
        if not data or not isinstance(data, list):
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos


def get_repo_traffic(token: str, full_name: str) -> dict:
    # Grab views, clones, referrers, paths
    h = make_headers(token)
    views   = _safe_get(f"{BASE}/repos/{full_name}/traffic/views",             h)
    clones  = _safe_get(f"{BASE}/repos/{full_name}/traffic/clones",            h)
    refs    = _safe_get(f"{BASE}/repos/{full_name}/traffic/popular/referrers", h)
    paths   = _safe_get(f"{BASE}/repos/{full_name}/traffic/popular/paths",     h)

    return {
        "views":     views  if isinstance(views,  dict) else {},
        "clones":    clones if isinstance(clones, dict) else {},
        "referrers": refs   if isinstance(refs,   list) else [],
        "paths":     paths  if isinstance(paths,  list) else [],
    }


# ── Building the data row ──────────────────────────────────────────────────────

def build_row(repo: dict, traffic: dict) -> dict:
    # Flatten repo + traffic into one row
    views   = traffic["views"]
    clones  = traffic["clones"]
    refs    = traffic["referrers"]
    paths   = traffic["paths"]

    return {
        "Repository":         repo["full_name"],
        "Private":            repo.get("private", False),
        "Stars":              repo.get("stargazers_count", 0),
        "Forks":              repo.get("forks_count", 0),
        "Total Views":        views.get("count",   0),
        "Unique Visitors":    views.get("uniques", 0),
        "Total Clones":       clones.get("count",   0),
        "Unique Cloners":     clones.get("uniques", 0),
        "Top Referrer":       refs[0].get("referrer",  "") if refs  else "",
        "Top Referrer Views": refs[0].get("count",      0) if refs  else 0,
        "Top Path":           paths[0].get("path",     "") if paths else "",
        "Top Path Views":     paths[0].get("count",     0) if paths else 0,
        "Fetched At":         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        # Raw lists kept for UI charts
        "_daily_views":       views.get("views",   []),
        "_daily_clones":      clones.get("clones", []),
        "_referrers":         refs,
        "_paths":             paths,
    }


# ── High-level fetch (used by both CLI and Streamlit) ─────────────────────────

def fetch_all_traffic(token: str, progress_cb=None) -> pd.DataFrame:
    # Fetch every repo's traffic, return DataFrame
    repos = get_all_repos(token)
    rows  = []
    total = max(len(repos), 1)

    for i, repo in enumerate(repos):
        traffic = get_repo_traffic(token, repo["full_name"])
        rows.append(build_row(repo, traffic))
        if progress_cb:
            progress_cb((i + 1) / total)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    # Export display columns to CSV bytes
    cols = [c for c in df.columns if not c.startswith("_")]
    buf  = io.StringIO()
    df[cols].to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
