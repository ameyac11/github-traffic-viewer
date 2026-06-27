"""
gitlytics/api.py
Powers the FastAPI backend — serves traffic data and the React dashboard to the browser.
"""
import hashlib
import logging
import os
import shutil
import time as _time
import uuid
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Body, File, Header, Response, UploadFile
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
    fetch_star_history,
    GitHubRateLimitError,
    StarHistoryFetchError,
)
from gitlytics.process import process_uploaded_csv, build_react_payload

logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Traffic API")

# Only allow requests from localhost — never deployed publicly.
# Vite's dev port (5173) is intentionally excluded from the production allowlist.
_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    # `Authorization` is required for cross-origin deployments that pass the
    # GitHub PAT in a header. Same-origin requests are unaffected.
    allow_headers=["Content-Type", "Authorization"],
)


_auth_cache: dict = {}  # sha256_prefix -> (valid, username, expires_at)
_AUTH_CACHE_TTL = 300  # 5 minutes

# Hard cap on CSV upload size — prevents DoS via /api/upload-csv.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _get_token(token: str = None) -> str:
    # C-2: explicit empty string must not fall through to the env token
    if token and token.strip():
        return token.strip()
    return os.environ.get("GITLYTICS_TOKEN")


def _validate_token_cached(token: str):
    # M-1: cache validation results to avoid a double HTTP round-trip on every /api/traffic call
    from gitlytics.core import validate_token as _validate_token
    key = hashlib.sha256(token.encode()).hexdigest()[:16]
    now = _time.time()
    if key in _auth_cache:
        valid, username, expires = _auth_cache[key]
        if now < expires:
            return valid, username
    valid, username = _validate_token(token)
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
        # Distinguish "user found" (login matches the request) from "GitHub failed
        # and we returned a stub". Returning 200 for the latter would silently mask
        # upstream outages.
        if profile.get("login") == username.strip() and profile.get("html_url"):
            pass
        elif profile.get("login") == username.strip():
            # Found but GitHub didn't include html_url — still treat as success.
            pass
        else:
            raise HTTPException(status_code=502, detail="GitHub did not return a profile.")
        repos = get_public_repos(username.strip())
        return {"profile": profile, "repos": repos}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
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

    # Build a quick view-sum map to find the top 20 repos for deep fetching.
    # Guard against the subset-metrics case where `views` may be absent.
    repos_with_views = []
    if (
        not df.empty
        and "repository" in df.columns
        and "views" in df.columns
    ):
        for repo_name, group in df.groupby("repository"):
            repos_with_views.append({"repository": repo_name, "total_views": int(group["views"].sum())})

    # Fetch deep stats concurrently for the top 20 most-viewed repos
    deep_stats = {}
    if repos_with_views and active_token:
        deep_stats = fetch_deep_stats_for_top(active_token, repos_with_views, top_n=20)

    payload = build_react_payload(df, deep_stats=deep_stats)
    return payload


# Star history endpoint — sampled star timeline for the SPA chart.
# Accepts the token via Authorization: Bearer header (PAT) so the chart
# can hit its own backend without exposing the token to the cloud.
# Falls back to GITLYTICS_TOKEN env so the local widget still works
# for users who stored their PAT in env instead of the LoginView.
@app.get("/api/star-history")
def get_star_history_endpoint(
    owner: str,
    repo: str,
    response: Response,
    authorization: str | None = Header(default=None),
):
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    token = bearer or os.environ.get("GITLYTICS_TOKEN")
    try:
        points = fetch_star_history(owner, repo, token)
    except GitHubRateLimitError as exc:
        # Surface rate-limit hits as 429 so the SPA shows the chart's rate-limit UI.
        raise HTTPException(status_code=429, detail=str(exc))
    except StarHistoryFetchError as exc:
        # Validation / metadata / network failures are caller errors — 400 makes more
        # sense than 429 here so the SPA can distinguish "GitHub is throttling us"
        # from "your request was malformed".
        raise HTTPException(status_code=400, detail=str(exc))
    response.headers["Cache-Control"] = "public, max-age=86400"
    return {"owner": owner, "repo": repo, "points": points}


@app.post("/api/upload-csv")
def upload_csv(file: UploadFile = File(...)):
    try:
        data_dir = os.environ.get("GITLYTICS_DATA_DIR")
        if data_dir:
            data_dir_path = Path(data_dir)
            data_dir_path.mkdir(parents=True, exist_ok=True)
            # Stream the upload to disk so we don't buffer the whole file in
            # memory. Enforce the size cap on the way in.
            dest = data_dir_path / f"traffic_uploaded_{uuid.uuid4().hex}.csv"
            total = 0
            with open(dest, "wb") as out:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _MAX_UPLOAD_BYTES:
                        out.close()
                        try:
                            dest.unlink()
                        except OSError:
                            pass
                        raise HTTPException(
                            status_code=413,
                            detail=f"CSV too large. Maximum size is {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                        )
                    out.write(chunk)
            file.file.seek(0)
        df = process_uploaded_csv(file.file)
        df = df.replace([float('inf'), float('-inf')], None).where(pd.notnull(df), None)
        payload = build_react_payload(df, deep_stats=None)
        return payload
    except HTTPException:
        raise
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
        content={"error": "Dashboard assets not found in the package installation."}
    )


@app.get("/{full_path:path}")
def serve_spa_fallback(full_path: str):
    """SPA catch-all — returns index.html so React Router handles navigation."""
    # Any unhandled /api/* path is a real 404, not a SPA route.
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"error": "Not found."})

    asset_file = frontend_dir / full_path
    if asset_file.exists() and asset_file.is_file():
        return FileResponse(asset_file)

    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return JSONResponse(
        status_code=503,
        content={"error": "Dashboard assets not found in the package installation."}
    )


assets_dir = frontend_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
