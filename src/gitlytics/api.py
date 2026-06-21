"""
gitlytics/api.py
Powers the FastAPI backend — serves traffic data and the React dashboard to the browser.
"""
import hashlib
import logging
import os
import time as _time
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Body, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gitlytics.core import (
    validate_token,
    get_user_profile,
    get_public_user,
    get_public_repos,
    fetch_traffic_data,
    fetch_deep_stats_for_top,
)
from gitlytics.process import process_uploaded_csv, build_react_payload

logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Traffic API")

# Only allow requests from localhost — never deployed publicly
_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


_auth_cache: dict = {}  # sha256_prefix -> (valid, username, expires_at)
_AUTH_CACHE_TTL = 300  # 5 minutes


def _get_token(token: str = None) -> str:
    # C-2: explicit empty string must not fall through to the env token
    if token and token.strip():
        return token.strip()
    return os.environ.get("GITLYTICS_TOKEN")


def _validate_token_cached(token: str):
    # M-1: cache validation results to avoid a double HTTP round-trip on every /api/traffic call
    key = hashlib.sha256(token.encode()).hexdigest()[:16]
    now = _time.time()
    if key in _auth_cache:
        valid, username, expires = _auth_cache[key]
        if now < expires:
            return valid, username
    from gitlytics.core import validate_token
    valid, username = validate_token(token)
    _auth_cache[key] = (valid, username, now + _AUTH_CACHE_TTL)
    return valid, username


@app.get("/api/config")
def get_config():
    return {
        "has_token": bool(os.environ.get("GITLYTICS_TOKEN")),
        "has_data_dir": bool(os.environ.get("GITLYTICS_DATA_DIR"))
    }


@app.post("/api/auth")
def auth(token: str = Body("", embed=True)):
    # Validate the token and return the user's GitHub profile info
    active_token = _get_token(token)
    if not active_token:
        raise HTTPException(status_code=401, detail="No token provided and no environment token found.")

    ok, username = validate_token(active_token)
    if not ok:
        logger.warning("Authentication attempt failed for a provided token.")
        raise HTTPException(status_code=401, detail=username)

    profile = get_user_profile(active_token)

    return {
        "authenticated": True,
        "username": profile["login"] or username,
        "name": profile["name"] or username,
        "avatar_url": profile["avatar_url"],
        "bio": profile.get("bio"),
        "location": profile.get("location"),
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
    }


@app.post("/api/username")
def get_username_data(username: str = Body("", embed=True)):
    """Fetches public profile and repos for any GitHub username — no token required."""
    if not username or not username.strip():
        raise HTTPException(status_code=400, detail="Username is required.")
    try:
        profile = get_public_user(username.strip())
        repos = get_public_repos(username.strip())
        return {"profile": profile, "repos": repos}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.warning(f"Username fetch failed for {username}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch GitHub data.")


@app.post("/api/traffic")
def get_traffic(token: str = Body("", embed=True)):
    # Serve traffic data — either from the historical CSV database or live from GitHub
    active_token = _get_token(token)
    if not active_token:
        raise HTTPException(status_code=401, detail="No token provided")

    ok, _ = _validate_token_cached(active_token)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid token")
    data_dir = os.environ.get("GITLYTICS_DATA_DIR")
    dfs = []
    if data_dir:
        data_dir_path = Path(data_dir)
        if not data_dir_path.exists():
            logger.warning(f"Data directory '{data_dir}' does not exist.")
        else:
            csv_files = list(data_dir_path.glob("traffic_*.csv"))
            if not csv_files:
                logger.warning(f"No traffic_*.csv files found in '{data_dir}'.")
            for f in csv_files:
                try:
                    dfs.append(pd.read_csv(f))
                except Exception as exc:
                    logger.warning(f"Skipping unreadable CSV '{f}': {exc}")

    try:
        live_df = fetch_traffic_data(active_token)
    except Exception as exc:
        logger.warning(f"Failed to fetch live traffic: {exc}")
        live_df = pd.DataFrame()

    if dfs:
        csv_df = pd.concat(dfs, ignore_index=True)
        if not live_df.empty:
            df = pd.concat([csv_df, live_df], ignore_index=True)
        else:
            df = csv_df
    else:
        df = live_df

    if not df.empty:
        df = df.drop_duplicates(subset=["date", "repository"], keep="last")

    df = df.replace([float('inf'), float('-inf')], None).where(pd.notnull(df), None)

    # Build a quick view-sum map to find the top 20 repos for deep fetching
    repos_with_views = []
    if not df.empty and "repository" in df.columns and "views" in df.columns:
        for repo_name, group in df.groupby("repository"):
            repos_with_views.append({"repository": repo_name, "total_views": int(group["views"].sum())})

    # Fetch deep stats concurrently for the top 20 most-viewed repos
    deep_stats = {}
    if repos_with_views and active_token:
        deep_stats = fetch_deep_stats_for_top(active_token, repos_with_views, top_n=20)

    payload = build_react_payload(df, deep_stats=deep_stats)
    return payload


@app.post("/api/upload-csv")
def upload_csv(file: UploadFile = File(...)):
    # Accept a user-uploaded CSV — deep stats not available in CSV mode
    try:
        df = process_uploaded_csv(file.file)
        df = df.replace([float('inf'), float('-inf')], None).where(pd.notnull(df), None)
        payload = build_react_payload(df, deep_stats=None)
        return payload
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Static file serving
frontend_dir = Path(__file__).parent / "static"


@app.get("/")
def serve_index():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(
        status_code=503,
        content={"error": "Dashboard not found. Run 'npm run build' in the dashboard directory."}
    )


@app.get("/{full_path:path}")
def serve_spa_fallback(full_path: str):
    """SPA catch-all — returns index.html so React Router handles navigation."""
    asset_file = frontend_dir / full_path
    if asset_file.exists() and asset_file.is_file():
        return FileResponse(asset_file)

    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return JSONResponse(
        status_code=503,
        content={"error": "Dashboard not found. Run 'npm run build' in the dashboard directory."}
    )


assets_dir = frontend_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
