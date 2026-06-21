"""
gitlytics/__init__.py
The public API for the gitlytics package.
"""
import os
import logging
import json

# Single source of truth for the package version.
# Mirrors the version in pyproject.toml — keep them in sync.
__version__ = "0.1.7"

__all__ = ["fetch_traffic", "sync", "serve_dashboard", "__version__"]

# Import the internal building blocks — users never call these directly
from .core import fetch_traffic_data, print_repo_table
from .automation import run_sync
from .process import build_json_payload

# Set up a silent logger so gitlytics never messes with your app's logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def fetch_traffic(token: str, repo_name=None, print_table: bool = False, return_format: str = "dataframe", save_file: str = None, metrics: list = None):
    """
    Fetches the last 14 days of traffic data for one or all repositories.

    Args:
        token: GitHub Personal Access Token with `repo` scope.
        repo_name: Specific repo name (e.g. ``"user/repo"``) or list of names.
            If ``None``, fetches all repositories accessible by the token.
        print_table: If ``True``, prints an ASCII summary table to stdout.
        return_format: Shape of the returned data. One of:
            ``"dataframe"`` (default) — returns a ``pandas.DataFrame``.
            ``"timeseries"`` — returns a nested JSON-serialisable dict.
            ``"summary"`` — returns a per-repo totals dict.
        save_file: Optional path to save the output. Extension determines
            format: ``.json`` writes JSON, anything else writes CSV.
        metrics: Optional list of metrics to fetch (e.g., ``["views", "clones"]``).

    Returns:
        A ``pandas.DataFrame`` when ``return_format="dataframe"``, otherwise
        a ``dict`` matching the requested format.
    """
    # Hit the GitHub API and get back a tidy DataFrame (one row per day per repo)
    df = fetch_traffic_data(token, repo_name, metrics)

    # Print the ASCII table to the console if the user asked for it
    if print_table:
        print_repo_table(df)

    # --- dataframe mode: just return the raw DataFrame, optionally save it ---
    if return_format == "dataframe":
        if save_file:
            if save_file.endswith(".json"):
                # Save as a chart-ready JSON file
                payload = build_json_payload(df, return_format="timeseries", export_public_only=True)
                with open(save_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
            else:
                # Save as a standard CSV file
                df.to_csv(save_file, index=False)
        return df

    # Reject anything that isn't a known format before doing more work
    valid_formats = {"timeseries", "summary"}
    if return_format not in valid_formats:
        raise ValueError(
            f"Invalid return_format={return_format!r}. "
            f"Choose one of: 'dataframe', 'timeseries', 'summary'."
        )

    # Build the JSON-serialisable payload in the requested shape
    payload = build_json_payload(df, return_format=return_format, export_public_only=False)

    # Save to disk if the user gave us a file path
    if save_file:
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    return payload


def sync(token: str, repo_name=None, data_dir: str = "./data", output_mode: str = "monthly", schedule_cron: str = None, export_json: str = None, export_public_only: bool = True, metrics: list = None):
    """
    Fetches data and appends it to a local CSV database, optionally running as a permanent background daemon.

    Args:
        token: GitHub Personal Access Token.
        repo_name: Specific repository name(s) to sync. If ``None``, syncs all.
        data_dir: Directory where CSV files are stored.
        output_mode: ``"monthly"`` (``traffic_YYYY-MM.csv``) or ``"yearly"`` (``traffic_YYYY.csv``).
        schedule_cron: Standard cron expression (e.g. ``"0 23 * * *"``). If set,
            runs an infinite scheduler loop.
        export_json: Path to export the merged historical database as a JSON file.
        export_public_only: If ``True`` (default), strips private repos from the
            exported JSON — acts as a security firewall.
        metrics: Optional list of metrics to fetch (e.g., ``["views", "clones"]``).
    """
    if data_dir and not os.path.isabs(data_dir) and not os.path.exists(data_dir):
        parent_dir = os.path.join("..", data_dir)
        if os.path.exists(parent_dir):
            data_dir = parent_dir

    # Hand off to the automation engine — it handles deduplication and schema migration
    run_sync(
        token=token,
        repo_names=repo_name,
        data_dir=data_dir,
        output_mode=output_mode,
        schedule_cron=schedule_cron,
        export_json=export_json,
        export_public_only=export_public_only,
        metrics=metrics
    )


def serve_dashboard(host: str = "127.0.0.1", port: int = 8000, token: str = None, data_dir: str = None):
    """
    Starts the React + FastAPI dashboard server.

    ``uvicorn`` and ``fastapi`` are optional dependencies installed via::

        pip install "gitlytics[dashboard]"

    Args:
        host: Host IP to bind. Use ``"0.0.0.0"`` to listen on all interfaces.
        port: Port number (default ``8000``).
        token: Optional GitHub token — pre-authenticates the dashboard session.
        data_dir: Optional path to the historical CSV database directory.
    """
    # Only import uvicorn when the user actually calls serve_dashboard,
    # so the base `pip install gitlytics` doesn't crash without it
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "The dashboard requires additional dependencies. "
            "Install them with: pip install \"gitlytics[dashboard]\""
        )

    # M-7: save original values so they are restored when the server stops
    _orig_token = os.environ.get("GITLYTICS_TOKEN")
    _orig_data_dir = os.environ.get("GITLYTICS_DATA_DIR")
    try:
        if token:
            os.environ["GITLYTICS_TOKEN"] = token
        if data_dir:
            from pathlib import Path
            abs_data_dir = os.path.abspath(data_dir)
            if not os.path.exists(abs_data_dir) and not os.path.isabs(data_dir):
                parent_dir = os.path.abspath(os.path.join("..", data_dir))
                if os.path.exists(parent_dir):
                    abs_data_dir = parent_dir
            if not os.path.exists(abs_data_dir):
                print(f"⚠️ Warning: The specified data directory '{data_dir}' (resolved to '{abs_data_dir}') does not exist.")
            elif not any(Path(abs_data_dir).glob("traffic_*.csv")):
                print(f"⚠️ Warning: No traffic_*.csv database files found in '{data_dir}' (resolved to '{abs_data_dir}').")
            os.environ["GITLYTICS_DATA_DIR"] = abs_data_dir
        uvicorn.run("gitlytics.api:app", host=host, port=port, reload=False)
    finally:
        if _orig_token is None:
            os.environ.pop("GITLYTICS_TOKEN", None)
        else:
            os.environ["GITLYTICS_TOKEN"] = _orig_token
        if _orig_data_dir is None:
            os.environ.pop("GITLYTICS_DATA_DIR", None)
        else:
            os.environ["GITLYTICS_DATA_DIR"] = _orig_data_dir
