"""
gitlytics/process.py
Handles processing Tidy DataFrames into final JSON formats for the dashboard.
"""
import ast
import json
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


def build_json_payload(df: pd.DataFrame, return_format: str = "timeseries", export_public_only: bool = True) -> dict:
    """Transforms the Tidy Data DataFrame into the nested JSON structure."""
    if df.empty:
        return {"account_totals": {}, "repositories": {}}

    if export_public_only and "is_private" in df.columns:
        df = df[~df["is_private"]]

    if df.empty:
        return {"account_totals": {}, "repositories": {}}

    account_views = 0
    account_clones = 0
    account_uniques = 0
    account_unique_cloners = 0
    account_stars = 0
    account_forks = 0

    repos_dict = {}

    for repo, group in df.groupby("repository"):
        group = group.sort_values("date")

        r_views = _safe_int(group["views"].sum()) if "views" in group.columns else 0
        r_clones = _safe_int(group["clones"].sum()) if "clones" in group.columns else 0
        r_unique_v = _safe_int(group["unique_visitors"].sum()) if "unique_visitors" in group.columns else 0
        r_unique_c = _safe_int(group["unique_cloners"].sum()) if "unique_cloners" in group.columns else 0
        r_stars = _safe_int(group["stars"].dropna().iloc[-1]) if "stars" in group.columns and not group["stars"].dropna().empty else 0
        r_forks = _safe_int(group["forks"].dropna().iloc[-1]) if "forks" in group.columns and not group["forks"].dropna().empty else 0
        r_is_private = bool(group["is_private"].dropna().iloc[-1]) if "is_private" in group.columns and not group["is_private"].dropna().empty else False

        top_ref = str(group["top_referrer"].dropna().iloc[-1]) if "top_referrer" in group.columns and not group["top_referrer"].dropna().empty else ""
        top_path = str(group["top_path"].dropna().iloc[-1]) if "top_path" in group.columns and not group["top_path"].dropna().empty else ""

        account_views += r_views
        account_clones += r_clones
        account_uniques += r_unique_v
        account_unique_cloners += r_unique_c
        account_stars += r_stars
        account_forks += r_forks

        if return_format == "summary":
            repos_dict[repo] = {
                "is_private": r_is_private,
                "total_views": r_views,
                "total_clones": r_clones,
                "unique_visitors": r_unique_v,
                "unique_cloners": r_unique_c,
                "stars": r_stars,
                "forks": r_forks
            }
        else:
            timeseries = []
            for _, row in group.iterrows():
                timeseries.append({
                    "date": str(row["date"]),
                    "views": int(row.get("views", 0)),
                    "unique_visitors": int(row.get("unique_visitors", 0)),
                    "clones": int(row.get("clones", 0)),
                    "unique_cloners": int(row.get("unique_cloners", 0))
                })

            repos_dict[repo] = {
                "timeseries": timeseries,
                "totals": {
                    "is_private": r_is_private,
                    "stars": r_stars,
                    "forks": r_forks,
                    "top_referrer": top_ref,
                    "top_path": top_path
                }
            }

    account_totals = {
        "total_views": account_views,
        "total_clones": account_clones,
        "unique_visitors": account_uniques,
        "unique_cloners": account_unique_cloners,
        "total_stars": account_stars,
        "total_forks": account_forks
    }

    return {
        "account_totals": account_totals,
        "repositories": repos_dict
    }


def process_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Reads a user-uploaded CSV and normalises column names to match our tidy schema."""
    raw_df = pd.read_csv(uploaded_file)

    # Normalise capitalized "Date" column before any other checks
    if "Date" in raw_df.columns and "date" not in raw_df.columns:
        raw_df = raw_df.rename(columns={"Date": "date"})

    if "repository" not in raw_df.columns:
        if "repo_name" in raw_df.columns:
            raw_df = raw_df.rename(columns={"repo_name": "repository"})
        elif "Repository" in raw_df.columns:
            raw_df = raw_df.rename(columns={
                "Repository": "repository", "Total Views": "views", "Unique Visitors": "unique_visitors",
                "Total Clones": "clones", "Unique Cloners": "unique_cloners", "Stars": "stars", "Forks": "forks"
            })
        else:
            raise ValueError("Invalid CSV format: missing 'repository' column")

    if "date" not in raw_df.columns:
        raise ValueError("Invalid CSV format: missing required 'date' column")
    return raw_df


def _parse_raw(val) -> list:
    # Try JSON first, then Python literal eval, then give up
    if isinstance(val, str) and val.strip() != "":
        try:
            return json.loads(val)
        except Exception:
            try:
                return ast.literal_eval(val)
            except Exception:
                return []
    if isinstance(val, list):
        return val
    return []


def _safe_int(val, fallback=0) -> int:
    try:
        return int(val) if val is not None and str(val) not in ("", "nan", "None") else fallback
    except Exception:
        return fallback


def _safe_str(val, fallback="") -> str:
    if val is None or str(val) in ("nan", "None", ""):
        return fallback
    return str(val)


def build_react_payload(df: pd.DataFrame, deep_stats: dict = None) -> list:
    """
    Transforms the Tidy DataFrame into the RepoTraffic array the React dashboard expects.
    Optionally merges in deep stats (commits, PRs, releases, README) for the top 20 repos.
    """
    if df.empty:
        return []

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repos = []

    for repo, group in df.groupby("repository"):
        group = group.sort_values("date")

        r_views = _safe_int(group["views"].sum()) if "views" in group.columns else 0
        r_clones = _safe_int(group["clones"].sum()) if "clones" in group.columns else 0
        r_unique_v = _safe_int(group["unique_visitors"].sum()) if "unique_visitors" in group.columns else 0
        r_unique_c = _safe_int(group["unique_cloners"].sum()) if "unique_cloners" in group.columns else 0
        r_stars = _safe_int(group["stars"].dropna().iloc[-1]) if "stars" in group.columns and not group["stars"].dropna().empty else 0
        r_forks = _safe_int(group["forks"].dropna().iloc[-1]) if "forks" in group.columns and not group["forks"].dropna().empty else 0
        r_is_private = bool(group["is_private"].dropna().iloc[-1]) if "is_private" in group.columns and not group["is_private"].dropna().empty else False

        top_ref = _safe_str(group["top_referrer"].dropna().iloc[-1]) if "top_referrer" in group.columns and not group["top_referrer"].dropna().empty else ""
        top_ref_views = _safe_int(group["top_referrer_views"].dropna().iloc[-1]) if "top_referrer_views" in group.columns and not group["top_referrer_views"].dropna().empty else 0
        top_ref_uniques = _safe_int(group["top_referrer_uniques"].dropna().iloc[-1]) if "top_referrer_uniques" in group.columns and not group["top_referrer_uniques"].dropna().empty else 0
        top_path = _safe_str(group["top_path"].dropna().iloc[-1]) if "top_path" in group.columns and not group["top_path"].dropna().empty else ""
        top_path_views = _safe_int(group["top_path_views"].dropna().iloc[-1]) if "top_path_views" in group.columns and not group["top_path_views"].dropna().empty else 0
        top_path_uniques = _safe_int(group["top_path_uniques"].dropna().iloc[-1]) if "top_path_uniques" in group.columns and not group["top_path_uniques"].dropna().empty else 0

        # Repo-level metadata from the CSV rows (populated by build_tidy_rows)
        language = _safe_str(group["language"].dropna().iloc[-1]) if "language" in group.columns and not group["language"].dropna().empty else None
        watchers_count = _safe_int(group["watchers_count"].dropna().iloc[-1]) if "watchers_count" in group.columns and not group["watchers_count"].dropna().empty else 0
        open_issues_count = _safe_int(group["open_issues_count"].dropna().iloc[-1]) if "open_issues_count" in group.columns and not group["open_issues_count"].dropna().empty else 0
        pushed_at = _safe_str(group["pushed_at"].dropna().iloc[-1]) if "pushed_at" in group.columns and not group["pushed_at"].dropna().empty else None
        created_at = _safe_str(group["created_at"].dropna().iloc[-1]) if "created_at" in group.columns and not group["created_at"].dropna().empty else None

        # Topics stored as JSON string in CSV
        topics_raw = group["topics"].dropna().iloc[-1] if "topics" in group.columns and not group["topics"].dropna().empty else None
        topics = _parse_raw(topics_raw) if topics_raw else []

        # Daily arrays for charts
        daily_views = []
        daily_clones = []
        for _, row in group.iterrows():
            date_str = str(row["date"])
            daily_views.append({
                "timestamp": date_str,
                "count": _safe_int(row.get("views", 0)),
                "uniques": _safe_int(row.get("unique_visitors", 0))
            })
            daily_clones.append({
                "timestamp": date_str,
                "count": _safe_int(row.get("clones", 0)),
                "uniques": _safe_int(row.get("unique_cloners", 0))  # fixed typo
            })

        raw_refs_val = group["_raw_referrers"].iloc[-1] if "_raw_referrers" in group.columns else None
        raw_paths_val = group["_raw_paths"].iloc[-1] if "_raw_paths" in group.columns else None
        full_refs = _parse_raw(raw_refs_val)
        full_paths = _parse_raw(raw_paths_val)

        if not full_refs and top_ref:
            full_refs = [{"referrer": top_ref, "count": top_ref_views, "uniques": top_ref_uniques}]
        if not full_paths and top_path:
            full_paths = [{"path": top_path, "title": top_path, "count": top_path_views, "uniques": top_path_uniques}]

        # Start building the repo object
        repo_obj = {
            "repository": repo,
            "is_private": r_is_private,
            "stars": r_stars,
            "forks": r_forks,
            "views": r_views,
            "unique_visitors": r_unique_v,
            "clones": r_clones,
            "unique_cloners": r_unique_c,
            "top_referrer": top_ref,
            "top_referrer_views": top_ref_views,
            "top_referrer_uniques": top_ref_uniques,
            "top_path": top_path,
            "top_path_views": top_path_views,
            "top_path_uniques": top_path_uniques,
            "fetched_at": fetched_at,
            # Repo metadata (available from GitHub API, None for CSV uploads)
            "language": language if language else None,
            "topics": topics if topics else [],
            "watchers_count": watchers_count,
            "open_issues_count": open_issues_count,
            "pushed_at": pushed_at,
            "created_at": created_at,
            # Deep stats — None by default, only populated for top 20 in Live API mode
            "total_commits": None,
            "open_prs": None,
            "total_releases": None,
            "last_release_at": None,
            "has_readme": None,
            "has_license": None,
            "has_contributing": None,
            "has_code_of_conduct": None,
            "_daily_views": daily_views,
            "_daily_clones": daily_clones,
            "_referrers": full_refs,
            "_paths": full_paths
        }

        # Merge deep stats if available for this repo
        if deep_stats and repo in deep_stats:
            ds = deep_stats[repo]
            for key in ("total_commits", "open_prs", "total_releases", "last_release_at",
                        "has_readme", "has_license", "has_contributing", "has_code_of_conduct"):
                if ds.get(key) is not None:
                    repo_obj[key] = ds[key]

        repos.append(repo_obj)

    return repos
