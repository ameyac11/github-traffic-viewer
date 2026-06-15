

"""
streamlit_app.py
Frontend only — all logic imported from github_traffic_fetch.py.

Run with:
    streamlit run streamlit_app.py
"""

import sys
from datetime import datetime, timezone as _tz
import streamlit as st
import pandas as pd

# Import all logic from our module
from github_traffic.core import (
    validate_token,
    fetch_all_traffic,
    to_csv_bytes,
)
from github_traffic.process import process_uploaded_csv

GITHUB_REPO = "https://github.com/ameyac11/github-traffic-monitor"
GITHUB_LOGO = """
<svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" fill="currentColor" style="display:block;flex-shrink:0;">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.01.08-2.1 0 0 .67-.21 2.2.82a7.68 7.68 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.09.16 1.9.08 2.1.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"></path>
</svg>
"""

# ── Guard against running with plain Python ───────────────────────────────────
if not st.runtime.exists():
    print("\n❌  Use:  streamlit run streamlit_app.py\n")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
#  Page config — must come first
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GitHub Traffic Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
#  Styles — dark, clean, minimal
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Base font and background */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    background-color: #0d1117;
    color: #c9d1d9;
}

/* Hide Streamlit deploy button and branding */
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
/* Sidebar background */

section[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #21262d;
}
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    overflow: hidden !important;
}

/* Tighten main area — pull content up, use top space */
.stApp [data-testid="stAppViewContainer"] .main .block-container,
.block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 0.25rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}
.stApp [data-testid="stMainBlockContainer"] {
    gap: 0.35rem !important;
}
.stApp [data-testid="stMainBlockContainer"] > div {
    gap: 0.35rem !important;
}

/* Top dashboard toolbar */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #161b22 !important;
    border-color: #21262d !important;
    border-radius: 10px !important;
    margin-bottom: 0.65rem !important;
    padding: 0.55rem 0.75rem !important;
}
.dash-header-block {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 52px;
}
.dash-header-block img {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 2px solid #30363d;
    flex-shrink: 0;
}
.dash-header-title {
    font-weight: 700;
    font-size: 1.05rem;
    color: #e6edf3;
    line-height: 1.15;
    margin: 0;
}
.dash-header-meta {
    font-size: 0.76rem;
    color: #8b949e;
    line-height: 1.35;
    margin-top: 2px;
}
.dash-header-user {
    font-size: 0.82rem;
    color: #c9d1d9;
    font-weight: 500;
}
.dashboard-hero {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 1rem 1.1rem;
    border: 1px solid #21262d;
    border-radius: 14px;
    background: linear-gradient(180deg, rgba(22,27,34,0.98), rgba(13,17,23,0.96));
    box-shadow: 0 10px 28px rgba(0,0,0,0.22);
}
.dashboard-hero img {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: 2px solid #30363d;
    flex-shrink: 0;
}
.dashboard-hero-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 800;
    color: #e6edf3;
    letter-spacing: -0.02em;
}
.dashboard-hero-subtitle {
    margin-top: 2px;
    font-size: 0.82rem;
    color: #8b949e;
    line-height: 1.45;
}
.dashboard-hero-link {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.5rem;
    padding: 0.35rem 0.65rem;
    border: 1px solid #30363d;
    border-radius: 999px;
    background: #161b22;
    color: #c9d1d9;
    text-decoration: none;
    font-size: 0.78rem;
}
.sidebar-repo-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 0.45rem 0.7rem;
    border: 1px solid #30363d;
    border-radius: 999px;
    background: #161b22;
    color: #c9d1d9 !important;
    text-decoration: none !important;
    font-size: 0.78rem;
    opacity: 1 !important;
    filter: none !important;
}
.sidebar-repo-link:hover {
    border-color: #58a6ff;
    color: #e6edf3 !important;
}
.sidebar-fetching-note {
    margin-top: 1rem;
    padding: 0.75rem 0.9rem;
    border: 1px solid #21262d;
    border-radius: 10px;
    background: #0d1117;
    color: #c9d1d9;
    font-size: 0.78rem;
    line-height: 1.5;
    text-align: center;
}
.toolbar-label {
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #8b949e;
    margin: 0 0 2px 0;
    line-height: 1;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] {
    align-items: flex-end !important;
    flex-wrap: nowrap !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .stTextInput > div {
    margin-bottom: 0 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stSlider"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stSlider"] [data-testid="stWidgetLabel"] {
    display: none !important;
}

/* Toolbar action buttons — compact single row */
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stDownloadButton"] > button {
    width: 100% !important;
    padding: 0.38rem 0.55rem !important;
    font-size: 0.78rem !important;
    min-height: 2.1rem !important;
    white-space: nowrap !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .stTextInput > div[data-baseweb="input"] {
    min-height: 2.4rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .stTextInput input {
    font-size: 0.9rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .toolbar-logout .stButton > button,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"]:last-child [data-testid="column"]:nth-child(3) .stButton > button {
    background-color: #3d1214 !important;
    border-color: #6e3035 !important;
    color: #ff7b72 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .toolbar-logout .stButton > button:hover,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="column"]:last-child [data-testid="column"]:nth-child(3) .stButton > button:hover {
    background-color: #5a1a1f !important;
    border-color: #ff7b72 !important;
}

/* Sidebar connect button */
section[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
}

/* Token password field container */
.stTextInput > div[data-baseweb="input"] {
    background-color: #0d1117 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.stTextInput > div[data-baseweb="input"]:focus-within {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.12) !important;
}

/* Inner input field styling */
.stTextInput input {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #e6edf3 !important;
    font-size: 0.875rem;
}
.stTextInput input:focus {
    outline: none !important;
    border: none !important;
}

/* Hide 'Press Enter to apply' hint to prevent overlap with eye icon */
div[data-testid="InputInstructions"] {
    display: none !important;
}

/* Standard Action Buttons */
.stButton > button, [data-testid="stDownloadButton"] > button {
    width: 100%;
    background-color: #21262d !important;
    color: #c9d1d9 !important;
    border: 1px solid rgba(240, 246, 252, 0.1) !important;
    border-radius: 6px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
}
.stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
    background-color: #30363d !important;
    border-color: #8b949e !important;
}

/* Hide Streamlit stale ghost widgets - removed for debugging */

/* Metric cards */
[data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 0.8rem 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.35);
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #58a6ff, #3fb950);
    opacity: 0;
    transition: opacity 0.2s;
}
[data-testid="metric-container"]:hover {
    border-color: #30363d;
    box-shadow: 0 6px 24px rgba(0,0,0,0.45);
    transform: translateY(-2px);
}
[data-testid="metric-container"]:hover::before { opacity: 1; }

[data-testid="metric-container"] label {
    color: #8b949e !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    color: #e6edf3 !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { color: #3fb950 !important; font-size: 0.8rem !important; }

/* Expandable repo sections */
[data-testid="stExpander"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    margin-bottom: 8px;
    transition: border-color 0.2s;
}
[data-testid="stExpander"]:hover { border-color: #30363d; }
[data-testid="stExpander"] summary {
    color: #e6edf3 !important;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.85rem 1rem;
}

/* Data tables */
[data-testid="stDataFrame"] {
    border: 1px solid #21262d;
    border-radius: 10px;
    overflow: hidden;
}

/* Loading bar */
[data-testid="stProgressBar"] > div {
    background: linear-gradient(90deg, #1f6feb, #58a6ff) !important;
    border-radius: 4px;
}

/* Divider lines */
hr { border: none; border-top: 1px solid #21262d; margin: 1rem 0; }

/* Thin custom scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }

/* GitHub corner button */
.github-corner-btn {
    position: fixed;
    top: 1rem;
    right: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 999px;
    padding: 0.4rem 0.8rem;
    color: #c9d1d9 !important;
    text-decoration: none !important;
    font-size: 0.85rem;
    font-weight: 600;
    z-index: 999999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transition: all 0.2s ease;
}
.github-corner-btn:hover {
    background: #30363d;
    border-color: #8b949e;
    color: #e6edf3 !important;
    transform: translateY(-1px);
}
.github-corner-btn svg {
    fill: currentColor;
}

/* Hide 200MB limit text in file uploader */
[data-testid="stFileUploader"] small {
    display: none !important;
}

/* Custom styling for the landing page */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    gap: 0.75rem !important;
    background: transparent !important;
    width: 100% !important;
}
div[data-testid="stRadio"] label {
    flex: 1 !important;
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
    cursor: pointer !important;
    margin: 0 !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background: #111b29 !important;
    border: 1px solid #1f6feb !important;
    border-bottom: 4px solid #1f6feb !important;
}
div[data-testid="stRadio"] label [data-testid="stMarker"] {
    display: none !important;
}
div[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] {
    display: flex;
    flex-direction: column;
    justify-content: center;
}
div[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p {
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    color: #c9d1d9 !important;
    margin: 0 !important;
}
div[data-testid="stRadio"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: #58a6ff !important;
}
div[data-testid="stRadio"] label:nth-child(1) [data-testid="stMarkdownContainer"]::after {
    content: "Real-time data from GitHub API";
    font-size: 0.75rem;
    color: #8b949e;
    font-weight: 400;
    margin-top: 0.25rem;
}
div[data-testid="stRadio"] label:nth-child(2) [data-testid="stMarkdownContainer"]::after {
    content: "Upload and analyze CSV files";
    font-size: 0.75rem;
    color: #8b949e;
    font-weight: 400;
    margin-top: 0.25rem;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.landing-card) {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 12px !important;
    padding: 1.25rem !important;
    margin-bottom: 1rem !important;
}

.stButton > button[kind="primary"] {
    background: #1f6feb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #388bfd !important;
}

[data-testid="stTextInput"] div[data-baseweb="input"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}
[data-testid="stTextInput"] input {
    color: #c9d1d9 !important;
}

/* Spacer CSS removed for debugging */
</style>
""", unsafe_allow_html=True)




# ─────────────────────────────────────────────────────────────────────────────
#  Session state — initialise once
# ─────────────────────────────────────────────────────────────────────────────
# Default values for first run
DEFAULTS = {
    "authenticated": False,
    "token":         "",
    "username":      "",
    "name":          "",
    "avatar_url":    "",
    "df":            None,
    "fetched":       False,
    "_is_fetching":   False,
    "repo_filter":   "",
    "landing_mode":  "Live API Fetch",
    "top_n_slider":   10,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


def _reset_session_state() -> None:
    """Return the dashboard to its logged-out defaults without wiping widget state wholesale."""
    for key, val in DEFAULTS.items():
        st.session_state[key] = val


def _repo_short_name(repo_name: str) -> str:
    """Return a safe display name for a repository."""
    return repo_name.rsplit("/", 1)[-1] if repo_name else "Repository"



def _connect_with_token(token_input: str) -> None:
    """Validate a GitHub PAT and update session state on success."""
    if not token_input.strip():
        st.error("Please enter your token first.", icon="⚠️")
        return

    with st.spinner("Authenticating…"):
        ok, uname, avatar, name = validate_token(token_input.strip())

    if ok:
        st.session_state.update({
            "authenticated": True,
            "token":         token_input.strip(),
            "username":      uname,
            "name":          name or uname,
            "avatar_url":    avatar,
            "fetched":       False,
            "df":            None,
            "_is_fetching":  True,
            "repo_filter":   "",
        })
        st.rerun()
    else:
        st.error(f"❌ {uname}", icon="🚫")


def _render_dashboard_toolbar(df: pd.DataFrame | None) -> tuple[str, int]:
    """Compact control bar: filters, top N, and actions."""

    with st.container(border=True):
        search_col, slider_col, csv_col, reload_col, logout_col = st.columns(
            [2.8, 1.8, 1.0, 1.0, 1.0],
            vertical_alignment="bottom",
            gap="medium",
        )

        with search_col:
            st.markdown('<p class="toolbar-label">Filter</p>', unsafe_allow_html=True)
            st.text_input(
                "Search",
                placeholder="Search repos…",
                label_visibility="collapsed",
                key="repo_filter",
            )
            search = st.session_state.get("repo_filter", "").strip()

        with slider_col:
            st.markdown('<p class="toolbar-label">Top N</p>', unsafe_allow_html=True)
            if df is not None and not df.empty:
                _slider_max = max(1, min(30, len(df)))
                _slider_min = min(1, _slider_max)
                _slider_def = min(10, _slider_max)
                top_n = st.slider(
                    "Show top N",
                    _slider_min, _slider_max, _slider_def,
                    key="top_n_slider", label_visibility="collapsed",
                )
            else:
                top_n = st.session_state.get("top_n_slider", 10)
                st.slider(
                    "Show top N",
                    1, 30, top_n,
                    key="top_n_slider", label_visibility="collapsed", disabled=True,
                )

        with csv_col:
            if df is not None and not df.empty:
                fname = f"github_traffic_{datetime.now(_tz.utc).strftime('%Y-%m-%d')}.csv"
                st.download_button(
                    label="⬇ CSV", data=to_csv_bytes(df), file_name=fname,
                    mime="text/csv", key="dl_btn", use_container_width=True
                )
            else:
                st.button("⬇ CSV", key="dl_btn_disabled", disabled=True, use_container_width=True)

        with reload_col:
            def _reload_cb():
                st.session_state.fetched = False
                st.session_state.df = None
                st.session_state._is_fetching = True
                st.session_state.repo_filter = ""
            st.button("↻ Reload", key="fetch_btn", on_click=_reload_cb, use_container_width=True)

        with logout_col:
            def _logout_cb():
                _reset_session_state()
            st.button("Logout", key="logout_btn", on_click=_logout_cb, use_container_width=True)

    return search, top_n


def _render_dashboard_hero() -> None:
    """Render the dashboard identity block at the top of the content area."""
    updated = datetime.now(_tz.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.markdown(
        f"""
        <div class="dashboard-hero">
            <img src="{st.session_state.avatar_url}" alt="Profile" />
            <div>
                <p class="dashboard-hero-title">GitHub Traffic Dashboard</p>
                <div class="dash-header-user">{st.session_state.name} · @{st.session_state.username}</div>
                <div class="dashboard-hero-subtitle">14-day analytics for all your repos, updated {updated}. Private and fast (token cleared on refresh).</div>
                <a class="dashboard-hero-link" href="{GITHUB_REPO}" target="_blank" rel="noopener noreferrer">
                    {GITHUB_LOGO}<span>Open repository</span>
                </a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


DISPLAY_COLS = [
    "Repository", "Private", "Stars", "Forks",
    "Total Views", "Unique Visitors", "Total Clones", "Unique Cloners",
    "Top Referrer", "Top Referrer Views", "Top Path", "Top Path Views",
]


def _normalize_dashboard_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Ensure the dashboard always receives the columns it expects."""
    normalized = frame.copy()
    defaults = {
        "Repository": "",
        "Private": False,
        "Stars": 0,
        "Forks": 0,
        "Total Views": 0,
        "Unique Visitors": 0,
        "Total Clones": 0,
        "Unique Cloners": 0,
        "Top Referrer": "",
        "Top Referrer Views": 0,
        "Top Path": "",
        "Top Path Views": 0,
        "_daily_views": [],
        "_daily_clones": [],
        "_referrers": [],
        "_paths": [],
    }
    for column, default_value in defaults.items():
        if column not in normalized.columns:
            normalized[column] = default_value

    normalized["Repository"] = normalized["Repository"].fillna("").astype(str)
    normalized["Private"] = normalized["Private"].fillna(False).astype(bool)

    numeric_cols = [
        "Stars",
        "Forks",
        "Total Views",
        "Unique Visitors",
        "Total Clones",
        "Unique Cloners",
        "Top Referrer Views",
        "Top Path Views",
    ]
    for column in numeric_cols:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce").replace([float("inf"), float("-inf")], 0).fillna(0)

    return normalized


def _search_filter_frame(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    q = query.strip()
    if not q:
        return frame.copy()
    names = frame["Repository"].astype(str)
    shorts = names.str.split("/").str[-1]
    mask = (
        names.str.contains(q, case=False, na=False)
        | shorts.str.contains(q, case=False, na=False)
    )
    return frame[mask].copy()


def _prepare_ranked_chart_frame(frame: pd.DataFrame, value_column: str, top_n: int) -> pd.DataFrame:
    chart_frame = frame.copy()
    chart_frame[value_column] = pd.to_numeric(chart_frame[value_column], errors="coerce")
    chart_frame[value_column] = chart_frame[value_column].replace([float("inf"), float("-inf")], 0).fillna(0)
    chart_frame = chart_frame.nlargest(top_n, value_column)
    return chart_frame


def _prepare_daily_chart_frame(entries: list[dict], value_labels: dict[str, str]) -> pd.DataFrame | None:
    if not entries:
        return None

    chart_frame = pd.DataFrame(entries)
    if chart_frame.empty or "timestamp" not in chart_frame.columns:
        return None

    chart_frame = chart_frame.copy()
    chart_frame["timestamp"] = pd.to_datetime(chart_frame["timestamp"], errors="coerce", utc=True)
    chart_frame = chart_frame.dropna(subset=["timestamp"])
    if chart_frame.empty:
        return None

    for column, label in value_labels.items():
        if column not in chart_frame.columns:
            chart_frame[column] = 0
        chart_frame[column] = pd.to_numeric(chart_frame[column], errors="coerce").replace([float("inf"), float("-inf")], 0).fillna(0)

    chart_frame["date"] = chart_frame["timestamp"].dt.strftime("%Y-%m-%d")
    chart_frame = chart_frame.groupby("date", as_index=True)[list(value_labels.keys())].sum()
    chart_frame = chart_frame.rename(columns=value_labels)
    return chart_frame if not chart_frame.empty else None


def _safe_max(series: pd.Series) -> int:
    """Helper to safely compute max value for ProgressColumn without causing Infinity/NaN crashes."""
    val = series.max()
    if not pd.notna(val) or val == float("inf") or val <= 0:
        return 1
    return int(val)


def _render_dashboard_content(df: pd.DataFrame, search: str, top_n: int) -> None:
    """Render metrics, charts, tables, and repo detail for the current filter."""
    active_df = _normalize_dashboard_frame(_search_filter_frame(df, search))

    st.markdown("<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin:0.5rem 0 0.5rem 0;'>Overview — Last 14 Days</p>", unsafe_allow_html=True)

    metrics_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
        <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 1.25rem;">
            <div style="color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; white-space: nowrap;">Repositories</div>
            <div style="color: #c9d1d9; font-size: 1.75rem; font-weight: 700;">{len(active_df):,}</div>
        </div>
        <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 1.25rem;">
            <div style="color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; white-space: nowrap;">Total Views</div>
            <div style="color: #c9d1d9; font-size: 1.75rem; font-weight: 700;">{int(active_df['Total Views'].sum()):,}</div>
        </div>
        <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 1.25rem;">
            <div style="color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; white-space: nowrap;">Unique Visitors</div>
            <div style="color: #c9d1d9; font-size: 1.75rem; font-weight: 700;">{int(active_df['Unique Visitors'].sum()):,}</div>
        </div>
        <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 1.25rem;">
            <div style="color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; white-space: nowrap;">Total Clones</div>
            <div style="color: #c9d1d9; font-size: 1.75rem; font-weight: 700;">{int(active_df['Total Clones'].sum()):,}</div>
        </div>
        <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 1.25rem;">
            <div style="color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; white-space: nowrap;">⭐ Stars</div>
            <div style="color: #c9d1d9; font-size: 1.75rem; font-weight: 700;">{int(active_df['Stars'].sum()):,}</div>
        </div>
        <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 1.25rem;">
            <div style="color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; white-space: nowrap;">🍴 Forks</div>
            <div style="color: #c9d1d9; font-size: 1.75rem; font-weight: 700;">{int(active_df['Forks'].sum()):,}</div>
        </div>
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)

    active_df = active_df.copy()
    # Drop duplicates to prevent st.bar_chart from crashing the frontend (blank screen) if API returns duplicate rows
    active_df = active_df.drop_duplicates(subset=["Repository"])
    active_df["_short"] = active_df["Repository"].str.split("/").str[-1]
    # Make _short unique by using full name for duplicates to prevent st.bar_chart crash
    dups = active_df.duplicated(subset=["_short"], keep=False)
    active_df.loc[dups, "_short"] = active_df.loc[dups, "Repository"]

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("<h4 style='color:#e6edf3;margin:0 0 1rem 0;font-size:0.95rem;font-weight:600;'>👁️ Top Repositories by Views</h4>", unsafe_allow_html=True)
            top_v = _prepare_ranked_chart_frame(active_df, "Total Views", top_n).set_index("_short")[["Total Views", "Unique Visitors"]]
            max_val = top_v["Total Views"].max() if not top_v.empty else 0
            if not top_v.empty and pd.notna(max_val) and max_val > 0 and max_val != float("inf"):
                st.bar_chart(top_v, color=["#58a6ff", "#3fb950"])
            else:
                st.info("No data to display.", icon="📊")

    with col2:
        with st.container(border=True):
            st.markdown("<h4 style='color:#e6edf3;margin:0 0 1rem 0;font-size:0.95rem;font-weight:600;'>📥 Top Repositories by Clones</h4>", unsafe_allow_html=True)
            top_c = _prepare_ranked_chart_frame(active_df, "Total Clones", top_n).set_index("_short")[["Total Clones", "Unique Cloners"]]
            max_val = top_c["Total Clones"].max() if not top_c.empty else 0
            if not top_c.empty and pd.notna(max_val) and max_val > 0 and max_val != float("inf"):
                st.bar_chart(top_c, color=["#ff7b72", "#e3b341"])
            else:
                st.info("No data to display.", icon="📊")

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("<h4 style='color:#e6edf3;margin:0 0 1rem 0;font-size:0.95rem;font-weight:600;'>⭐ Most Starred</h4>", unsafe_allow_html=True)
            top_s = _prepare_ranked_chart_frame(active_df, "Stars", top_n).set_index("_short")[["Stars"]]
            max_val = top_s["Stars"].max() if not top_s.empty else 0
            if not top_s.empty and pd.notna(max_val) and max_val > 0 and max_val != float("inf"):
                st.bar_chart(top_s, color="#e3b341")
            else:
                st.info("No data to display.", icon="📊")

    with col4:
        with st.container(border=True):
            st.markdown("<h4 style='color:#e6edf3;margin:0 0 1rem 0;font-size:0.95rem;font-weight:600;'>🍴 Most Forked</h4>", unsafe_allow_html=True)
            top_f = _prepare_ranked_chart_frame(active_df, "Forks", top_n).set_index("_short")[["Forks"]]
            max_val = top_f["Forks"].max() if not top_f.empty else 0
            if not top_f.empty and pd.notna(max_val) and max_val > 0 and max_val != float("inf"):
                st.bar_chart(top_f, color="#a371f7")
            else:
                st.info("No data to display.", icon="📊")

    st.markdown("<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin:2rem 0 0.75rem 0;'>All Repositories</p>", unsafe_allow_html=True)

    table_df = active_df.sort_values(
        ["Total Clones", "Total Views"],
        ascending=[False, False],
    )

    st.dataframe(
        table_df[DISPLAY_COLS],
        width="stretch",
        height=400,
        hide_index=True,
        column_config={
            "Repository":         st.column_config.TextColumn("Repository", width="medium", help="Full repository name"),
            "Private":            st.column_config.CheckboxColumn("Private", help="Is the repository private?"),
            "Stars":              st.column_config.NumberColumn("Stars ⭐", format="%d"),
            "Forks":              st.column_config.NumberColumn("Forks 🍴", format="%d"),
            "Total Views":        st.column_config.ProgressColumn("Views", format="%d", min_value=0, max_value=_safe_max(active_df["Total Views"]) if not active_df.empty else 1),
            "Unique Visitors":    st.column_config.NumberColumn("Visitors 👥", format="%d"),
            "Total Clones":       st.column_config.ProgressColumn("Clones", format="%d", min_value=0, max_value=_safe_max(active_df["Total Clones"]) if not active_df.empty else 1),
            "Unique Cloners":     st.column_config.NumberColumn("Cloners 👥", format="%d"),
            "Top Referrer":       st.column_config.TextColumn("Top Referrer"),
            "Top Referrer Views": st.column_config.NumberColumn("Referrer Views", format="%d"),
            "Top Path":           st.column_config.TextColumn("Top Path"),
            "Top Path Views":     st.column_config.NumberColumn("Path Views", format="%d"),
        },
    )

    st.markdown("<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin:2rem 0 0.75rem 0;'>Repository Detail</p>", unsafe_allow_html=True)

    filtered = active_df.sort_values(
        ["Total Clones", "Total Views"],
        ascending=[False, False],
    )

    if filtered.empty:
        st.info("No repositories match your search.")

    for _, row in filtered.iterrows():
        is_private  = row["Private"]
        vis_label   = "🔒 Private" if is_private else "🌐 Public"
        vis_color   = "#f78166"    if is_private else "#3fb950"
        label = f"{_repo_short_name(str(row['Repository']))}  ·  {int(row['Total Views']):,} views  ·  {int(row['Total Clones']):,} clones"

        with st.expander(label):
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;">
                <span style="font-size:0.875rem;font-weight:700;color:#e6edf3;">{row['Repository']}</span>
                <span style="font-size:0.7rem;font-weight:600;color:{vis_color};
                             background:{vis_color}18;border:1px solid {vis_color}40;
                             border-radius:20px;padding:1px 9px;">{vis_label}</span>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Views",           f"{int(row['Total Views']):,}")
            m2.metric("Unique Visitors", f"{int(row['Unique Visitors']):,}")
            m3.metric("Clones",          f"{int(row['Total Clones']):,}")
            m4.metric("Unique Cloners",  f"{int(row['Unique Cloners']):,}")
            m5.metric("⭐ Stars",         f"{int(row['Stars']):,}")
            m6.metric("🍴 Forks",         f"{int(row['Forks']):,}")

            d_views  = row.get("_daily_views",  [])
            d_clones = row.get("_daily_clones", [])

            if d_views or d_clones:
                ch1, ch2 = st.columns(2)

                if d_views:
                    with ch1:
                        dv = _prepare_daily_chart_frame(d_views, {"count": "Views", "uniques": "Unique"})
                        if dv is not None:
                                st.markdown("<p style='font-size:0.78rem;font-weight:600;color:#8b949e;margin-bottom:4px;'>📅 Daily Views</p>", unsafe_allow_html=True)
                                st.line_chart(dv, color=["#58a6ff", "#1f6feb"])

                if d_clones:
                    with ch2:
                        dc = _prepare_daily_chart_frame(d_clones, {"count": "Clones", "uniques": "Unique"})
                        if dc is not None:
                                st.markdown("<p style='font-size:0.78rem;font-weight:600;color:#8b949e;margin-bottom:4px;'>📥 Daily Clones</p>", unsafe_allow_html=True)
                                st.line_chart(dc, color=["#f78166", "#ff7b72"])

            refs  = row.get("_referrers", [])
            paths = row.get("_paths",     [])

            if refs or paths:
                t1, t2 = st.columns(2)

                if refs:
                    with t1:
                        st.markdown("<p style='font-size:0.78rem;font-weight:600;color:#8b949e;margin-bottom:4px;'>🔗 Top Referrers</p>", unsafe_allow_html=True)
                        ref_df = pd.DataFrame(refs)[["referrer", "count", "uniques"]]
                        st.dataframe(
                            ref_df.rename(columns={"referrer": "Source", "count": "Views", "uniques": "Unique"}),
                            width="stretch",
                            hide_index=True,
                            height=180,
                        )

                if paths:
                    with t2:
                        st.markdown("<p style='font-size:0.78rem;font-weight:600;color:#8b949e;margin-bottom:4px;'>📄 Popular Paths</p>", unsafe_allow_html=True)
                        path_df = pd.DataFrame(paths)[["path", "count", "uniques"]]
                        st.dataframe(
                            path_df.rename(columns={"path": "Path", "count": "Views", "uniques": "Unique"}),
                            width="stretch",
                            hide_index=True,
                            height=180,
                        )


def _fetch_traffic_data() -> None:
    """Load traffic into session state, then rerun for a clean UI."""
    with st.status("Fetching GitHub Traffic Data...", expanded=True) as status:
        prog = st.progress(0, text="Fetching repositories…")

        def _on_progress(frac: float):
            prog.progress(frac, text=f"Fetching traffic…  {int(frac * 100)}%")

        df = fetch_all_traffic(st.session_state.token, progress_cb=_on_progress)
        status.update(label="Fetching complete!", state="complete", expanded=False)

    st.session_state.df = df
    st.session_state.fetched = True
    st.session_state._is_fetching = False
    st.rerun()


# ── Landing page — not logged in or fetching ──────────────────────────────────
if not st.session_state.fetched or st.session_state.df is None:
    if "landing_mode" not in st.session_state:
        st.session_state.landing_mode = "Live API Fetch"
        
    st.markdown("<style>[data-testid='stSidebar'] {display: none !important;} [data-testid='collapsedControl'] {display: none !important;}</style>", unsafe_allow_html=True)
    
    # Header
    st.markdown("""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; margin-top: 0;">
<div style="display: flex; align-items: center; gap: 0.75rem;">
<div style="background: #161b22; padding: 0.5rem; border-radius: 8px; border: 1px solid #21262d; display: flex; align-items: center; justify-content: center;">
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
</div>
<div>
<h1 style="margin: 0; font-size: 1.35rem; font-weight: 700; color: #e6edf3;">GitHub Traffic Dashboard</h1>
<p style="margin: 0; color: #8b949e; font-size: 0.85rem;">Monitor your repository traffic with real-time insights</p>
</div>
</div>
<a href="https://github.com/ameyac11/github-traffic-monitor" target="_blank" style="padding: 0.4rem 0.8rem; border: 1px solid #21262d; border-radius: 8px; color: #c9d1d9; text-decoration: none; display: flex; align-items: center; gap: 0.5rem; background: #161b22; font-size: 0.8rem; font-weight: 600;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
Docs
</a>
</div>""", unsafe_allow_html=True)
    
    left_col, empty_col, right_col = st.columns([1.2, 0.1, 1.0])
    
    with left_col:
        mode = st.radio(
            "Select Input Mode:",
            ["📈 Live API Fetch", "☁️ CSV Upload"],
            index=0 if st.session_state.landing_mode == "Live API Fetch" else 1,
            label_visibility="collapsed",
            horizontal=True,
            disabled=st.session_state.authenticated  # Disable while fetching
        )
        st.session_state.landing_mode = mode.replace("📈 ", "").replace("☁️ ", "")
        
        if st.session_state.landing_mode == "Live API Fetch":
            st.markdown("""<div style="background: #0d1117; border: 1px solid #21262d; border-radius: 12px; padding: 1.25rem; margin-top: 1rem;">
<div style="display: flex; gap: 0.75rem; margin-bottom: 1.25rem;">
<div style="background: #1f6feb; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0; font-size: 0.8rem;">i</div>
<div>
<h4 style="color: #e6edf3; margin: 0 0 0.25rem 0; font-size: 0.95rem; font-weight: 600;">What does this do?</h4>
<p style="color: #8b949e; margin: 0; font-size: 0.85rem; line-height: 1.4;">This mode connects directly to the GitHub API using your Personal Access Token (PAT). It fetches your repository traffic data (views, clones, stars, etc.) and visualizes it instantly.</p>
</div>
</div>
<div style="background: rgba(210, 153, 34, 0.1); border: 1px solid rgba(210, 153, 34, 0.2); border-radius: 8px; padding: 1rem; display: flex; gap: 0.75rem; margin-bottom: 1.25rem;">
<div style="color: #d29922; font-size: 1.1rem; flex-shrink: 0;">⚠️</div>
<div>
<h4 style="color: #e6edf3; margin: 0 0 0.25rem 0; font-size: 0.9rem; font-weight: 600;">14-Day Data Limit</h4>
<p style="color: #8b949e; margin: 0; font-size: 0.8rem; line-height: 1.4;">GitHub only provides up to 14 days of traffic history via the API. Data older than 2 weeks will not be available.</p>
</div>
</div>
<div style="background: rgba(31, 111, 235, 0.1); border: 1px solid rgba(31, 111, 235, 0.2); border-radius: 8px; padding: 1rem; display: flex; gap: 0.75rem;">
<div style="color: #58a6ff; font-size: 1.1rem; flex-shrink: 0;">📄</div>
<div>
<h4 style="color: #e6edf3; margin: 0 0 0.25rem 0; font-size: 0.9rem; font-weight: 600;">Need Historical Data?</h4>
<p style="color: #8b949e; margin: 0; font-size: 0.8rem; line-height: 1.4;">To save your data permanently and bypass this limit, use the <a href="https://github.com/ameyac11/github-traffic-monitor-automation" target="_blank" style="color: #58a6ff; text-decoration: none;">GitHub Traffic Automation Repository.</a> It runs a daily GitHub Action to save your data as CSVs, which you can upload in the CSV Upload mode.</p>
</div>
</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background: #0d1117; border: 1px solid #21262d; border-radius: 12px; padding: 1.25rem; margin-top: 1rem;">
<div style="display: flex; gap: 0.75rem; margin-bottom: 1.25rem;">
<div style="background: #1f6feb; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0; font-size: 0.8rem;">i</div>
<div>
<h4 style="color: #e6edf3; margin: 0 0 0.25rem 0; font-size: 0.95rem; font-weight: 600;">Visualize Permanent Data</h4>
<p style="color: #8b949e; margin: 0; font-size: 0.85rem; line-height: 1.4;">This mode allows you to upload the monthly CSV files generated by the GitHub Traffic Automation Repo.</p>
</div>
</div>
<div style="background: rgba(46, 160, 67, 0.1); border: 1px solid rgba(46, 160, 67, 0.2); border-radius: 8px; padding: 1rem; display: flex; gap: 0.75rem;">
<div style="color: #3fb950; font-size: 1.1rem; flex-shrink: 0;">💡</div>
<div>
<h4 style="color: #e6edf3; margin: 0 0 0.25rem 0; font-size: 0.9rem; font-weight: 600;">Why use CSVs?</h4>
<p style="color: #8b949e; margin: 0; font-size: 0.8rem; line-height: 1.4;">GitHub only saves 14 days of traffic data. The automation repository pulls your data daily and saves it permanently as CSVs. By uploading those files here, you can visualize months or years of historical traffic! No PAT token is required.</p>
</div>
</div>
</div>""", unsafe_allow_html=True)
            
        st.markdown("""<div style="margin-top: 1rem;">
<h4 style="color: #e6edf3; margin: 0 0 0.75rem 0; font-size: 0.95rem; font-weight: 600;">Resources</h4>
<div style="display: flex; gap: 0.75rem;">
<a href="https://github.com/ameyac11/github-traffic-monitor" target="_blank" style="flex: 1; background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 0.6rem 0.75rem; color: #c9d1d9; text-decoration: none; display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; font-weight: 500;">
<div style="display: flex; align-items: center; gap: 0.4rem;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>
Dashboard Repo
</div>
<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
</a>
<a href="https://github.com/ameyac11/github-traffic-monitor-automation" target="_blank" style="flex: 1; background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 0.6rem 0.75rem; color: #c9d1d9; text-decoration: none; display: flex; align-items: center; justify-content: space-between; font-size: 0.8rem; font-weight: 500;">
<div style="display: flex; align-items: center; gap: 0.4rem;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
Automation Repo
</div>
<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
</a>
</div>
</div>""", unsafe_allow_html=True)

        st.markdown("""<div style="text-align: center; margin-top: 2rem; color: #8b949e; font-size: 0.75rem;">
Built for developers &nbsp;&nbsp;•&nbsp;&nbsp; Open source &nbsp;&nbsp;•&nbsp;&nbsp; Apache 2.0 license
</div>""", unsafe_allow_html=True)

    with right_col:
        st.markdown("<div class='landing-spacer'></div>", unsafe_allow_html=True)
        
        if st.session_state.authenticated:
            # We are authenticated but data is not fetched yet -> Show the Avatar and Spinner here!
            st.markdown(f"""
            <div style="text-align:center; padding-top: 1rem; margin-bottom: 1.5rem;">
                <img src="{st.session_state.avatar_url}" width="80" style="border-radius:50%;border:3px solid #30363d;margin-bottom:1rem;box-shadow:0 8px 24px rgba(0,0,0,0.4);">
                <h2 style="color:#e6edf3;margin:0 0 0.25rem 0;">Welcome, {st.session_state.name}!</h2>
                <p style="color:#8b949e;font-size:0.9rem;margin:0;">@{st.session_state.username}</p>
            </div>
            """, unsafe_allow_html=True)
            _fetch_traffic_data()
            
        else:
            # We are not authenticated -> Show login or CSV form
            if st.session_state.landing_mode == "Live API Fetch":
                with st.container(border=True):
                    st.markdown('<div class="landing-card"></div>', unsafe_allow_html=True)
                    st.markdown("""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
<h3 style="margin: 0; font-size: 1.05rem; color: #e6edf3; font-weight: 600;">Connect Your GitHub Account</h3>
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
</div>
<p style="color: #8b949e; font-size: 0.8rem; margin-top: 0; margin-bottom: 1rem;">Enter your Personal Access Token (PAT) to get started</p>""", unsafe_allow_html=True)
                    
                    token_input = st.text_input(
                        "token",
                        type="password",
                        placeholder="🔑 Paste your PAT (ghp_...) here",
                        label_visibility="collapsed",
                        key="main_token_input"
                    )
                    
                    if st.button("Connect to GitHub", use_container_width=True, type="primary"):
                        if not token_input.strip():
                            st.error("Please enter a token first.")
                        else:
                            with st.spinner("Connecting to GitHub..."):
                                ok, uname, avatar, name = validate_token(token_input.strip())
                                if ok:
                                    st.session_state.update({
                                        "authenticated": True,
                                        "token":         token_input.strip(),
                                        "username":      uname,
                                        "name":          name or uname,
                                        "avatar_url":    avatar,
                                        "fetched":       False,
                                        "df":            None,
                                        "_is_fetching":  True,
                                        "repo_filter":   "",
                                    })
                                    st.rerun()
                                else:
                                    st.error(f"❌ Authentication failed: {uname}")

                    st.markdown("""<div style="text-align: center; margin-top: 0.75rem; color: #8b949e; font-size: 0.75rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem;">
<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg>
Your token is encrypted and never stored.
</div>""", unsafe_allow_html=True)

                with st.container(border=True):
                    st.markdown('<div class="landing-card"></div>', unsafe_allow_html=True)
                    st.markdown("""<h3 style="margin: 0 0 1rem 0; font-size: 1.05rem; color: #e6edf3; font-weight: 600;">Security & Help</h3>
<div style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: flex-start;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-top: 0.1rem;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg>
<div>
<div style="color: #e6edf3; font-size: 0.85rem; font-weight: 500; margin-bottom: 0.1rem;">Security Notice</div>
<div style="color: #8b949e; font-size: 0.75rem;">Token is only kept in session memory and cleared on refresh.</div>
</div>
</div>
<hr style="border: 0; border-top: 1px solid #21262d; margin: 0.75rem 0;">
<a href="https://github.com/settings/tokens" target="_blank" style="display: flex; justify-content: space-between; align-items: center; text-decoration: none; padding: 0.25rem 0;">
<div style="display: flex; gap: 0.75rem; align-items: center;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
<span style="color: #c9d1d9; font-size: 0.85rem; font-weight: 500;">How to create a PAT</span>
</div>
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
</a>
<hr style="border: 0; border-top: 1px solid #21262d; margin: 0.75rem 0;">
<a href="https://docs.github.com/en/rest" target="_blank" style="display: flex; justify-content: space-between; align-items: center; text-decoration: none; padding: 0.25rem 0;">
<div style="display: flex; gap: 0.75rem; align-items: center;">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>
<span style="color: #c9d1d9; font-size: 0.85rem; font-weight: 500;">Learn more about GitHub API</span>
</div>
<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
</a>""", unsafe_allow_html=True)
                    
                with st.container(border=True):
                    st.markdown('<div class="landing-card"></div>', unsafe_allow_html=True)
                    st.markdown("""<div style="display: flex; gap: 0.6rem; margin-bottom: 0.75rem; align-items: center;">
<div style="color: #58a6ff;">💡</div>
<h3 style="margin: 0; font-size: 0.95rem; color: #58a6ff; font-weight: 600;">Quick Tips</h3>
</div>
<div style="display: flex; gap: 0.6rem; margin-bottom: 0.5rem; align-items: flex-start;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-top: 0.15rem; flex-shrink: 0;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
<span style="color: #8b949e; font-size: 0.8rem;">Use a token with 'repo' scope for private repositories</span>
</div>
<div style="display: flex; gap: 0.6rem; align-items: flex-start;">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-top: 0.15rem; flex-shrink: 0;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
<span style="color: #8b949e; font-size: 0.8rem;">Token expires? Generate a new one in your settings</span>
</div>""", unsafe_allow_html=True)

            else:
                with st.container(border=True):
                    st.markdown('<div class="landing-card"></div>', unsafe_allow_html=True)
                    st.markdown("""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
<h3 style="margin: 0; font-size: 1.05rem; color: #e6edf3; font-weight: 600;">Upload Monthly CSV</h3>
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8b949e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
</div>
<p style="color: #8b949e; font-size: 0.8rem; margin-top: 0; margin-bottom: 1rem;">Select your local CSV file to load the dashboard.</p>""", unsafe_allow_html=True)
                    
                    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
                    
                    if uploaded_file is not None:
                        if st.button("Load Dashboard", type="primary", use_container_width=True):
                            with st.spinner("Processing CSV data..."):
                                try:
                                    df = process_uploaded_csv(uploaded_file)
                                    st.session_state.update({
                                        "authenticated": True,
                                        "token":         "csv_upload",
                                        "username":      "local_data",
                                        "name":          "CSV Upload",
                                        "avatar_url":    "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
                                        "fetched":       True,
                                        "df":            df,
                                        "_is_fetching":  False,
                                        "repo_filter":   "",
                                    })
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error processing CSV: {e}")
                                    
                    st.markdown("""<div style="text-align: center; margin-top: 1rem; color: #8b949e; font-size: 0.75rem; display: flex; align-items: center; justify-content: center; gap: 0.4rem;">
<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg>
CSV processed locally. No data is stored or uploaded.
</div>""", unsafe_allow_html=True)



    st.stop()


# ── Full dashboard after data is loaded ───────────────────────────────────────
st.markdown("<style>[data-testid='stSidebar'] {display: none !important;} [data-testid='collapsedControl'] {display: none !important;}</style>", unsafe_allow_html=True)

_render_dashboard_hero()

try:
    df = st.session_state.df
    if df is None or df.empty:
        st.warning("No repositories found, or no traffic data available for this token.")
        st.stop()

    search, top_n = _render_dashboard_toolbar(df)
    _render_dashboard_content(df, search, top_n)
except Exception as exc:
    st.error("The dashboard hit an unexpected render error. Please refresh and try again.")
    st.exception(exc)

