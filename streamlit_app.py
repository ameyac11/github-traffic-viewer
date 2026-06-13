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
from github_traffic_fetch import (
    validate_token,
    fetch_all_traffic,
    to_csv_bytes,
)

GITHUB_REPO = "https://github.com/ameyac11/github-traffic-viewer"
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

/* Hide Streamlit deploy button and branding — keep sidebar toggle visible */
#MainMenu                            { visibility: hidden; }
footer                               { visibility: hidden; }
[data-testid="stDecoration"]         { display: none !important; }
[data-testid="stStatusWidget"]       { display: none !important; }
[data-testid="stHeaderDeployButton"],
[data-testid="stAppDeployButton"],
.stDeployButton,
.stAppDeployButton              { display: none !important; visibility: hidden !important; }
[data-testid="stElementToolbar"]     { display: none !important; }

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
.stApp [data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 0.5rem !important;
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

/* Hide Streamlit stale ghost widgets (faded duplicates during reruns) */
.stale,
[data-testid="stElementContainer"].stale,
div[data-testid="stVerticalBlock"].stale,
section[data-testid="stSidebar"] [style*="opacity: 0.5"],
section[data-testid="stSidebar"] [style*="opacity:0.5"],
section[data-testid="stSidebar"] [style*="opacity: 0.33"],
section[data-testid="stSidebar"] [style*="opacity:0.33"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

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
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

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
        search_col, slider_col, actions_col = st.columns(
            [2.7, 1.6, 3.3],
            vertical_alignment="bottom",
            gap="small",
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
                top_n = st.slider(
                    "Show top N",
                    5,
                    min(30, len(df)),
                    min(10, len(df)),
                    key="top_n_slider",
                    label_visibility="collapsed",
                )
            else:
                top_n = 10
                st.slider(
                    "Show top N",
                    5,
                    30,
                    10,
                    key="top_n_slider",
                    label_visibility="collapsed",
                    disabled=True,
                )

        with actions_col:
            st.markdown('<p class="toolbar-label">Actions</p>', unsafe_allow_html=True)
            btn1, btn2, btn3 = st.columns([1.0, 1.05, 0.95], gap="small", vertical_alignment="center")
            with btn1:
                if df is not None and not df.empty:
                    fname = f"github_traffic_{datetime.now(_tz.utc).strftime('%Y-%m-%d')}.csv"
                    st.download_button(
                        label="⬇ CSV",
                        data=to_csv_bytes(df),
                        file_name=fname,
                        mime="text/csv",
                        key="dl_btn",
                    )
                else:
                    st.button("⬇ CSV", key="dl_btn_disabled", disabled=True)
            with btn2:
                def _reload_cb():
                    st.session_state.fetched = False
                    st.session_state.df = None
                    st.session_state._is_fetching = True
                    st.session_state.repo_filter = ""
                st.button("↻ Reload", key="fetch_btn", on_click=_reload_cb)
            with btn3:
                def _logout_cb():
                    st.session_state.clear()
                st.button("Logout", key="logout_btn", on_click=_logout_cb)

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


def _render_dashboard_content(df: pd.DataFrame, search: str, top_n: int) -> None:
    """Render metrics, charts, tables, and repo detail for the current filter."""
    active_df = _search_filter_frame(df, search)

    st.markdown("<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin:0.5rem 0 0.5rem 0;'>Overview — Last 14 Days</p>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Repositories",    f"{len(active_df):,}")
    c2.metric("Total Views",     f"{int(active_df['Total Views'].sum()):,}")
    c3.metric("Unique Visitors", f"{int(active_df['Unique Visitors'].sum()):,}")
    c4.metric("Total Clones",    f"{int(active_df['Total Clones'].sum()):,}")
    c5.metric("⭐ Stars",         f"{int(active_df['Stars'].sum()):,}")
    c6.metric("🍴 Forks",         f"{int(active_df['Forks'].sum()):,}")

    st.markdown("<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#8b949e;margin:1.25rem 0 0.5rem 0;'>Top Repositories by Traffic</p>", unsafe_allow_html=True)

    active_df = active_df.copy()
    active_df["_short"] = active_df["Repository"].str.split("/").str[1]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<p style='font-size:0.8rem;font-weight:600;color:#c9d1d9;margin-bottom:0.5rem;'>👁️ Views</p>", unsafe_allow_html=True)
        top_v = active_df.nlargest(top_n, "Total Views").set_index("_short")[["Total Views", "Unique Visitors"]]
        st.bar_chart(top_v, color=["#58a6ff", "#3fb950"])

    with col2:
        st.markdown("<p style='font-size:0.8rem;font-weight:600;color:#c9d1d9;margin-bottom:0.5rem;'>📥 Clones</p>", unsafe_allow_html=True)
        top_c = active_df.nlargest(top_n, "Total Clones").set_index("_short")[["Total Clones", "Unique Cloners"]]
        st.bar_chart(top_c, color=["#ff7b72", "#e3b341"])

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("<p style='font-size:0.8rem;font-weight:600;color:#c9d1d9;margin-bottom:0.5rem;'>⭐ Stars</p>", unsafe_allow_html=True)
        st.bar_chart(active_df.nlargest(top_n, "Stars").set_index("_short")[["Stars"]], color=["#e3b341"])

    with col4:
        st.markdown("<p style='font-size:0.8rem;font-weight:600;color:#c9d1d9;margin-bottom:0.5rem;'>🍴 Forks</p>", unsafe_allow_html=True)
        st.bar_chart(active_df.nlargest(top_n, "Forks").set_index("_short")[["Forks"]], color=["#a371f7"])

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
            "Total Views":        st.column_config.ProgressColumn("Views", format="%d", min_value=0, max_value=int(active_df["Total Views"].max()) if not active_df.empty else 1),
            "Unique Visitors":    st.column_config.NumberColumn("Visitors 👥", format="%d"),
            "Total Clones":       st.column_config.ProgressColumn("Clones", format="%d", min_value=0, max_value=int(active_df["Total Clones"].max()) if not active_df.empty else 1),
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
        label = f"{row['Repository'].split('/')[1]}  ·  {int(row['Total Views']):,} views  ·  {int(row['Total Clones']):,} clones"

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
                        dv = pd.DataFrame(d_views)
                        dv["date"] = pd.to_datetime(dv["timestamp"]).dt.date
                        dv = dv.set_index("date")[["count", "uniques"]].rename(columns={"count": "Views", "uniques": "Unique"})
                        st.markdown("<p style='font-size:0.78rem;font-weight:600;color:#8b949e;margin-bottom:4px;'>📅 Daily Views</p>", unsafe_allow_html=True)
                        st.line_chart(dv, color=["#58a6ff", "#1f6feb"])

                if d_clones:
                    with ch2:
                        dc = pd.DataFrame(d_clones)
                        dc["date"] = pd.to_datetime(dc["timestamp"]).dt.date
                        dc = dc.set_index("date")[["count", "uniques"]].rename(columns={"count": "Clones", "uniques": "Unique"})
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


_SIDEBAR_LOGO = """
<div style="text-align:center; padding: 0.25rem 0 1rem 0;">
    <div style="font-size:2rem;">🚀</div>
    <div style="font-size:0.95rem; font-weight:700; color:#e6edf3;">GitHub Traffic</div>
    <div style="font-size:0.7rem; color:#8b949e; margin-top:2px;">Local Dashboard</div>
</div>
"""

_SIDEBAR_FOOTER = f"""
<div style="margin-top: 1rem; padding-top: 10px; border-top: 1px solid #21262d; text-align: center;">
    <div style="font-size:0.68rem;color:#8b949e;line-height:1.6;">
        🔒 Token is not saved (cleared on refresh)
    </div>
    <a class="sidebar-repo-link" href="{GITHUB_REPO}" target="_blank" rel="noopener noreferrer">
       {GITHUB_LOGO}<span>GitHub Repository</span></a>
</div>
"""


def _render_sidebar(mode: str) -> None:
    """Render sidebar for auth, fetching, or connected states — one layout per mode."""
    slot = st.sidebar.empty()
    with slot.container():
        st.markdown(_SIDEBAR_LOGO, unsafe_allow_html=True)

        if mode == "auth":
            st.markdown(
                "<p style='font-size:0.72rem;font-weight:600;letter-spacing:0.08em;"
                "text-transform:uppercase;color:#8b949e;margin-bottom:4px;'>Your GitHub Token</p>",
                unsafe_allow_html=True,
            )
            sidebar_token = st.text_input(
                "token",
                type="password",
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
                label_visibility="collapsed",
                key="token_widget_sidebar",
            )
            st.caption("Needs `repo` scope for private repos")
            if st.button("🔐  Connect to GitHub", key="connect_btn_sidebar"):
                _connect_with_token(sidebar_token)
            st.markdown(_SIDEBAR_FOOTER, unsafe_allow_html=True)

        elif mode == "fetching":
            st.markdown(
                "<div class='sidebar-fetching-note'>"
                "Fetching traffic data...<br>Keep this tab open while the dashboard loads."
                "</div>",
                unsafe_allow_html=True,
            )

        else:
            st.markdown("""
            <div style="background:#0d1117;border:1px solid #21262d;border-radius:10px;
                        padding:12px;text-align:center;margin-top:0.5rem;">
                <div style="font-size:0.8rem;color:#3fb950;font-weight:600;">✓ Connected</div>
                <div style="font-size:0.72rem;color:#8b949e;margin-top:4px;">
                    Use the toolbar at the top to manage your session.
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(_SIDEBAR_FOOTER, unsafe_allow_html=True)


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


# ── Landing page — not logged in ──────────────────────────────────────────────
if not st.session_state.authenticated:
    _render_sidebar("auth")

    st.markdown(f"""
    <div style="padding: 0 0 0.5rem 0; border-bottom: 1px solid #21262d; margin-bottom: 0.75rem;">
        <h1 style="font-size:1.6rem;font-weight:800;color:#e6edf3;margin:0 0 0.2rem 0;letter-spacing:-0.02em;">
            GitHub Traffic Dashboard
        </h1>
        <p style="font-size:0.85rem;color:#8b949e;margin:0;">
            14-day analytics for all your repos — fully private (token cleared on refresh).
            <a href="{GITHUB_REPO}" target="_blank" rel="noopener noreferrer"
               style="color:#58a6ff;text-decoration:none;display:inline-flex;align-items:center;gap:0.35rem;vertical-align:middle;">
               {GITHUB_LOGO}<span>View on GitHub</span></a>
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:12px;
                padding:2rem 2.5rem;max-width:560px;margin:1rem 0;">
        <h3 style="font-size:1rem;font-weight:700;color:#e6edf3;margin:0 0 0.75rem 0;">
            👈 Get started in 2 steps
        </h3>
        <ol style="color:#8b949e;font-size:0.875rem;line-height:2.2;margin:0;padding-left:1.25rem;">
            <li>Paste your <strong style="color:#c9d1d9">GitHub Personal Access Token</strong> in the sidebar</li>
            <li>Click <strong style="color:#3fb950">Connect to GitHub</strong></li>
        </ol>
        <div style="margin-top: 1rem; padding: 0.75rem; background: #3d1214; border: 1px solid #6e3035; border-radius: 8px;">
            <p style="font-size: 0.8rem; color: #ff7b72; margin: 0; line-height: 1.5;"><strong>⚠️ Security Notice:</strong> This app does not save your token. It is kept only in the session memory and is completely cleared upon refresh. If you are using a deployed web version of this dashboard, it is highly recommended to <strong>delete/revoke your token on GitHub</strong> after downloading your report.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖  How to create a Personal Access Token"):
        st.markdown("""
1. Go to **[GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)**
2. Click **Generate new token (classic)**
3. Give it a name like *Traffic Dashboard*
4. Check the **`repo`** scope
5. Generate and copy the token immediately
6. Paste it in the sidebar and click **Connect to GitHub**
""")
    st.stop()


# ── Fetch first — minimal sidebar so no duplicate ghost widgets ───────────────
if not st.session_state.fetched or st.session_state.df is None:
    _render_sidebar("fetching")
    _fetch_traffic_data()


# ── Full dashboard after data is loaded ───────────────────────────────────────
_render_sidebar("connected")
_render_dashboard_hero()

df = st.session_state.df
if df is None or df.empty:
    st.warning("No repositories found, or no traffic data available for this token.")
    st.stop()

search, top_n = _render_dashboard_toolbar(df)
_render_dashboard_content(df, search, top_n)
