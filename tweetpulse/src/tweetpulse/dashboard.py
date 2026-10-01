from __future__ import annotations

from html import escape
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import snowflake.connector
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from tweetpulse.config import LOCAL_BLOB_DIR, dashboard_mode, snowflake_config


st.set_page_config(page_title="TweetPulse", page_icon="TP", layout="wide")


BRAND_COLORS = {
    "positive": "#2f855a",
    "neutral": "#b7791f",
    "negative": "#c53030",
}
PRIMARY_BLUE = "#2563eb"
VIOLET = "#6d28d9"
ORANGE = "#c05621"
TEAL = "#0f766e"
INK = "#1f2937"
MUTED = "#6b7280"
CHART_CONFIG = {"displayModeBar": False, "responsive": True}
TREND_BUCKETS = {
    "15 minutes": "15min",
    "30 minutes": "30min",
    "1 hour": "h",
}
RANKING_METRICS = {
    "Total engagement": "engagement",
    "Post volume": "posts",
    "Avg engagement/post": "avg_engagement",
}


@st.cache_data(ttl=120)
def load_local_tweets(raw_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as file:
            rows.extend(json.loads(line) for line in file if line.strip())
    return normalize_tweets(pd.DataFrame(rows))


@st.cache_data(ttl=300)
def load_snowflake_tweets() -> pd.DataFrame:
    config = snowflake_config()
    connection_args = {
        "account": config.account,
        "user": config.user,
        "role": config.role,
        "warehouse": config.warehouse,
        "database": config.database,
        "schema": config.schema,
    }
    if config.authenticator == "externalbrowser":
        connection_args["authenticator"] = "externalbrowser"
    else:
        connection_args["password"] = config.password

    connection = snowflake.connector.connect(**connection_args)
    try:
        frame = pd.read_sql(
            """
            select
                tweet_id,
                author,
                text,
                topic,
                sentiment,
                likes,
                replies,
                reposts,
                engagement,
                created_at
            from analytics.vw_recent_tweets
            where created_at >= dateadd('day', -7, current_timestamp())
            """,
            connection,
        )
        frame.columns = [column.lower() for column in frame.columns]
        return normalize_tweets(frame)
    finally:
        connection.close()


def normalize_tweets(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    frame["created_at"] = pd.to_datetime(
        frame["created_at"],
        utc=True,
        format="mixed",
        errors="coerce",
    )
    frame = frame.dropna(subset=["created_at"])
    frame["minute"] = frame["created_at"].dt.floor("30min")
    frame["hour"] = frame["created_at"].dt.floor("h")
    frame["engagement"] = pd.to_numeric(frame["engagement"], errors="coerce").fillna(0)
    for column in ["likes", "replies", "reposts"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    frame["topic"] = frame["topic"].fillna("unknown").str.lower()
    frame["sentiment"] = frame["sentiment"].fillna("neutral").str.lower()
    return frame


def metric_value(value: float | int) -> str:
    return f"{value:,.0f}"


def metric_delta(value: float | int) -> int | float:
    numeric_value = float(value)
    if numeric_value.is_integer():
        return int(numeric_value)
    return numeric_value


def compact_number(value: float | int) -> str:
    numeric_value = float(value)
    if abs(numeric_value) >= 1_000_000:
        return f"{numeric_value / 1_000_000:.2f}M"
    if abs(numeric_value) >= 1_000:
        return f"{numeric_value / 1_000:.2f}K"
    return f"{numeric_value:,.0f}"


def decimal_value(value: float | int, suffix: str = "") -> str:
    return f"{float(value):,.2f}{suffix}"


def format_kpi_delta(value: float | int | None, suffix: str = "") -> tuple[str, str]:
    if value is None:
        return "", "neutral"
    numeric_value = float(value)
    if numeric_value > 0:
        return f"↑ {abs(numeric_value):,.2f}{suffix}", "positive"
    if numeric_value < 0:
        return f"↓ {abs(numeric_value):,.2f}{suffix}", "negative"
    return f"→ {abs(numeric_value):,.2f}{suffix}", "neutral"


def kpi_card(
    label: str,
    value: object,
    *,
    category: str = "neutral",
    icon: str = "",
    kpi_id: str = "",
    delta: float | int | None = None,
    delta_suffix: str = "",
    status: str | None = None,
    help_text: str = "",
) -> str:
    delta_text, delta_class = format_kpi_delta(delta, delta_suffix)
    badge = ""
    if status:
        badge_class = "muted" if status.lower() in {"not collected", "n/a"} else status.lower()
        badge = f'<span class="kpi-status {escape(badge_class)}">{escape(status)}</span>'
    elif delta_text:
        badge = f'<span class="kpi-delta {delta_class}">{escape(delta_text)}</span>'
    elif kpi_id:
        badge = f'<span class="kpi-id">{escape(kpi_id)}</span>'

    display_value = "N/A" if str(value).strip().lower() == "not collected" else str(value)
    help_block = f'<p>{escape(help_text)}</p>' if help_text else ""
    icon_text = icon or {
        "volume": "💬",
        "engagement": "👁",
        "sentiment": "☻",
        "audience": "👥",
        "content": "#",
        "quality": "!",
    }.get(category, "•")
    return (
        f'<div class="kpi-card {escape(category)}">'
        f'<div class="kpi-icon">{escape(icon_text)}</div>'
        '<div class="kpi-copy">'
        f'<div class="kpi-card-top"><span>{escape(label)}</span>{badge}</div>'
        f"<strong>{escape(display_value)}</strong>"
        f"{help_block}"
        "</div>"
        "</div>"
    )


def render_kpi_grid(cards: list[dict[str, object]], columns: int = 4) -> None:
    card_html = "".join(kpi_card(**card) for card in cards)
    st.markdown(
        f'<div class="kpi-grid" style="grid-template-columns: repeat({columns}, minmax(0, 1fr));">{card_html}</div>',
        unsafe_allow_html=True,
    )


def display_author(value: object) -> str:
    text = str(value)
    if text.startswith("did:plc:"):
        return f"{text.removeprefix('did:plc:')[:12]}..."
    return text[:32]


def rate(frame: pd.DataFrame, sentiment_name: str) -> float:
    if frame.empty:
        return 0
    return (frame["sentiment"].str.lower() == sentiment_name).mean() * 100


def build_sidebar_filters(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    nav_items = {
        "Executive Overview": "Overview",
        "Trend Analysis": "Engagement",
        "Topic Drilldown": "Audience",
        "Sentiment Intelligence": "Sentiment",
        "Tweet Explorer": "Alerts & Feed",
        "Data Quality": "Alerts & Feed",
    }
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-logo">TP</div>
            <div>
                <strong>TweetPulse</strong>
                <span>Bluesky Live Analytics</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Live social analytics powered by Bluesky Jetstream.")

    st.sidebar.markdown("#### Navigation")
    selected_nav = st.sidebar.radio(
        "Dashboard section",
        list(nav_items),
        label_visibility="collapsed",
    )
    selected_page = nav_items[selected_nav]

    topics = sorted(frame["topic"].dropna().unique())
    sentiments = sorted(frame["sentiment"].dropna().unique())

    title_col, date_col, topic_col, sentiment_col, source_col, refresh_col = st.columns(
        [4.2, 1.45, 1.25, 1.05, 1.25, 0.36],
        gap="small",
    )
    with title_col:
        st.markdown(
            f"""
            <div class="dashboard-title">
                <h1>TweetPulse <span>| Real-Time Social Intelligence</span></h1>
                <p>{escape(selected_nav)} dashboard for social volume, engagement, sentiment, and topic health.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with date_col:
        time_window = st.selectbox(
            "Date Range",
            ["Last 24 hours", "Last 7 days", "All loaded data"],
            index=1,
            key="top_time_window",
        )
    with topic_col:
        topic_filter = st.selectbox(
            "Topic",
            ["All Topics", *topics],
            index=0,
            key="top_topic_filter",
        )
    with sentiment_col:
        sentiment_filter = st.selectbox(
            "Sentiment",
            ["All", *sentiments],
            index=0,
            key="top_sentiment_filter",
        )
    with source_col:
        source_filter = st.selectbox(
            "Source",
            ["All Sources", "Snowflake" if dashboard_mode() == "snowflake" else "Local"],
            index=0,
            key="top_source_filter",
        )
    with refresh_col:
        st.markdown('<div class="refresh-spacer"></div>', unsafe_allow_html=True)
        if st.button("↻", key="refresh_dashboard", help="Refresh dashboard data"):
            st.cache_data.clear()
            st.rerun()

    st.sidebar.markdown("#### Advanced")
    trend_granularity = st.sidebar.selectbox("Trend granularity", list(TREND_BUCKETS), index=1)
    ranking_label = st.sidebar.selectbox("Rank topics by", list(RANKING_METRICS), index=0)
    top_n = st.sidebar.selectbox("Topics shown", [5, 10, 15, 20], index=1)

    max_engagement = int(frame["engagement"].max()) if not frame.empty else 0
    min_engagement = st.sidebar.slider(
        "Minimum engagement",
        min_value=0,
        max_value=max(max_engagement, 1),
        value=0,
        step=max(max(max_engagement // 100, 1), 1),
    )
    keyword = st.sidebar.text_input("Keyword search", placeholder="Search post text...")
    table_rows = st.sidebar.selectbox("Rows in post table", [10, 25, 50, 100], index=1)

    selected_topics = topics if topic_filter == "All Topics" else [topic_filter]
    selected_sentiments = sentiments if sentiment_filter == "All" else [sentiment_filter]

    filtered = frame.copy()
    if time_window != "All loaded data":
        hours = 24 if time_window == "Last 24 hours" else 24 * 7
        cutoff = filtered["created_at"].max() - pd.Timedelta(hours=hours)
        filtered = filtered[filtered["created_at"] >= cutoff]

    filtered = filtered[filtered["engagement"] >= min_engagement]
    filtered = filtered[filtered["topic"].isin(selected_topics)]
    filtered = filtered[filtered["sentiment"].isin(selected_sentiments)]
    if keyword.strip():
        filtered = filtered[
            filtered["text"].fillna("").str.contains(keyword.strip(), case=False, regex=False)
        ]

    latest_loaded = frame["created_at"].max()
    next_refresh = pd.Timestamp.now(tz="UTC") + pd.Timedelta(minutes=5)
    st.sidebar.markdown("#### Pipeline Status")
    st.sidebar.markdown(
        f"""
        <div class="pipeline-status">
            <div><span class="status-dot-mini"></span><strong>Pipeline active</strong></div>
            <p>Last loaded: {latest_loaded:%b %d, %I:%M %p UTC}</p>
            <p>Next dashboard refresh: {next_refresh:%I:%M %p UTC}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    controls = {
        "page": selected_page,
        "ranking_label": ranking_label,
        "ranking_metric": RANKING_METRICS[ranking_label],
        "table_rows": table_rows,
        "time_bucket": TREND_BUCKETS[trend_granularity],
        "time_window": time_window,
        "topic_label": topic_filter,
        "sentiment_label": sentiment_filter,
        "source_label": source_filter,
        "top_n": top_n,
        "trend_granularity": trend_granularity,
    }
    return filtered, controls


def style_chart(figure, height: int = 420):
    figure.update_layout(
        height=height,
        template="plotly_white",
        margin=dict(l=18, r=18, t=58, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(color=MUTED, family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", size=12),
        title=dict(font=dict(size=16, color=INK), x=0.015, xanchor="left"),
        legend_title_text="",
        hovermode="x unified",
        colorway=[PRIMARY_BLUE, "#2f855a", "#b7791f", VIOLET, ORANGE],
    )
    figure.update_xaxes(showgrid=False, linecolor="#e5e7eb", zeroline=False)
    figure.update_yaxes(gridcolor="#edf2f7", linecolor="#e5e7eb", zeroline=False)
    for trace in figure.data:
        trace.opacity = 0.86
        if trace.type not in {"histogram2d", "heatmap"} and hasattr(trace, "marker"):
            trace.marker.line.width = 0
    return figure


def format_duration(delta: pd.Timedelta) -> str:
    total_minutes = max(int(delta.total_seconds() // 60), 0)
    if total_minutes < 1:
        return "<1 min"
    if total_minutes < 60:
        return f"{total_minutes} min"
    total_hours = total_minutes // 60
    if total_hours < 48:
        return f"{total_hours} hr"
    return f"{total_hours // 24} days"


def latest_window_metrics(frame: pd.DataFrame) -> tuple[int, int, float, float]:
    if frame.empty:
        return 0, 0, 0, 0
    newest_timestamp = frame["created_at"].max()
    recent_start = newest_timestamp - pd.Timedelta(hours=1)
    previous_start = newest_timestamp - pd.Timedelta(hours=2)
    recent_frame = frame[frame["created_at"] >= recent_start]
    previous_frame = frame[
        (frame["created_at"] >= previous_start) & (frame["created_at"] < recent_start)
    ]
    return (
        recent_frame.shape[0],
        previous_frame.shape[0],
        recent_frame["engagement"].sum(),
        previous_frame["engagement"].sum(),
    )


def classify_alerts(
    frame: pd.DataFrame,
    trend_frame: pd.DataFrame,
    latest_age: pd.Timedelta,
    negative_rate: float,
) -> pd.DataFrame:
    alerts: list[dict[str, object]] = []
    newest_timestamp = frame["created_at"].max()

    if latest_age > pd.Timedelta(minutes=45):
        alerts.append(
            {
                "severity": "critical",
                "alert": "Pipeline freshness delay",
                "detail": f"Latest post is {format_duration(latest_age)} old.",
                "timestamp": newest_timestamp,
            }
        )

    if negative_rate >= 20:
        alerts.append(
            {
                "severity": "warning",
                "alert": "Negative sentiment elevated",
                "detail": f"Negative sentiment is {negative_rate:.1f}% in the selected window.",
                "timestamp": newest_timestamp,
            }
        )

    if trend_frame.shape[0] >= 3:
        mean_posts = trend_frame["posts"].mean()
        std_posts = trend_frame["posts"].std()
        latest_posts = trend_frame.sort_values("time_bucket").iloc[-1]["posts"]
        if std_posts and latest_posts > mean_posts + (2 * std_posts):
            alerts.append(
                {
                    "severity": "info",
                    "alert": "Volume spike detected",
                    "detail": f"Latest bucket has {int(latest_posts)} posts vs {mean_posts:.1f} average.",
                    "timestamp": newest_timestamp,
                }
            )

    if not alerts:
        alerts.append(
            {
                "severity": "healthy",
                "alert": "No active anomalies",
                "detail": "Pipeline freshness, volume, and sentiment are within expected range.",
                "timestamp": newest_timestamp,
            }
        )

    return pd.DataFrame(alerts)


def render_header(mode_name: str, controls: dict[str, object]) -> None:
    data_source = "Snowflake live warehouse" if mode_name == "snowflake" else "Local JSONL replay"
    page_name = str(controls["page"])
    source_label = "Snowflake" if mode_name == "snowflake" else "Local"
    st.markdown(
        f"""
        <section class="page-header">
            <div>
                <h1>TweetPulse <span>| Real-Time Social Intelligence</span></h1>
                <p>{escape(page_name)} dashboard for live social volume, engagement, sentiment, and topic health.</p>
            </div>
            <div class="filter-strip">
                <div class="filter-chip"><span>▣ Date Range</span><strong>{escape(str(controls["time_window"]))}</strong></div>
                <div class="filter-chip"><span>◇ Topic</span><strong>{escape(str(controls["topic_label"]))}</strong></div>
                <div class="filter-chip"><span>☻ Sentiment</span><strong>{escape(str(controls["sentiment_label"]))}</strong></div>
                <div class="filter-chip"><span>◎ Source</span><strong>{escape(source_label)}</strong></div>
                <div class="refresh-chip">↻</div>
            </div>
        </section>
        <div class="header-source"><span><i class="status-dot"></i> Pipeline active</span><strong>{escape(data_source)}</strong></div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="section-title">
            <h2>{title}</h2>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(label: str, value: object, detail: str) -> str:
    return (
        '<div class="insight-card">'
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(str(value))}</strong>"
        f"<p>{escape(detail)}</p>"
        "</div>"
    )


def render_insight_cards(cards: list[tuple[str, object, str]]) -> None:
    st.markdown(
        f'<div class="insight-grid">{"".join(insight_card(label, value, detail) for label, value, detail in cards)}</div>',
        unsafe_allow_html=True,
    )


mode = dashboard_mode()
if mode == "snowflake":
    st_autorefresh(interval=5 * 60 * 1000, key="tweetpulse_refresh")
    tweets = load_snowflake_tweets()
else:
    tweets = load_local_tweets(LOCAL_BLOB_DIR)

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .stApp {
        background: #f8fafc;
        color: #1f2937;
    }
    .block-container {
        padding-top: 1.15rem;
        padding-bottom: 3rem;
        max-width: 1540px;
    }
    .dashboard-title {
        padding-top: 0.2rem;
    }
    .dashboard-title h1 {
        color: #0f172a;
        font-size: 1.55rem;
        line-height: 1.15;
        letter-spacing: -0.02em;
        margin: 0;
        font-weight: 780;
    }
    .dashboard-title h1 span {
        font-weight: 680;
    }
    .dashboard-title p {
        margin: 0.28rem 0 0;
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.42;
    }
    section.page-header {
        display: flex;
        justify-content: space-between;
        gap: 1.1rem;
        align-items: center;
        padding: 0 0 1rem;
        margin-bottom: 0.35rem;
        border: none;
        border-radius: 0;
        background: transparent;
        box-shadow: none;
    }
    .page-header h1 {
        color: #0f172a;
        font-size: 1.55rem;
        line-height: 1.15;
        letter-spacing: -0.02em;
        margin: 0;
        font-weight: 780;
    }
    .page-header h1 span {
        font-weight: 680;
    }
    .page-header p {
        max-width: 760px;
        margin: 0.28rem 0 0;
        color: #64748b;
        font-size: 0.82rem;
        line-height: 1.42;
    }
    .filter-strip {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.65rem;
        flex-wrap: wrap;
    }
    .filter-chip {
        min-width: 128px;
        padding: 0.45rem 0.62rem;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: none;
        color: #0f172a;
    }
    .filter-chip span {
        display: block;
        color: #475569;
        font-size: 0.68rem;
        line-height: 1.1;
        font-weight: 700;
    }
    .filter-chip strong {
        display: block;
        color: #111827;
        font-size: 0.76rem;
        margin-top: 0.15rem;
        font-weight: 700;
    }
    .refresh-chip {
        display: grid;
        place-items: center;
        width: 42px;
        height: 42px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        color: #0f172a;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .header-source {
        display: none;
    }
    .status-dot {
        width: 0.45rem;
        height: 0.45rem;
        margin-right: 0.42rem;
        border-radius: 999px;
        background: #16a34a;
        border: none;
        box-shadow: none;
    }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.72rem;
        padding: 1.15rem 0.35rem 1.4rem;
        margin: 0;
        border: none;
        border-radius: 0;
        background: transparent;
    }
    .sidebar-logo {
        display: grid;
        place-items: center;
        width: 2rem;
        height: 2rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #0ea5e9, #2563eb);
        border: none;
        color: #ffffff;
        box-shadow: none;
        font-size: 0.8rem;
        font-weight: 800;
    }
    .sidebar-brand strong {
        display: block;
        color: #ffffff;
        line-height: 1.1;
        font-size: 1.35rem;
        letter-spacing: -0.015em;
        font-weight: 800;
    }
    .sidebar-brand span {
        display: none;
    }
    [data-testid="stSidebar"] {
        min-width: 245px;
        max-width: 285px;
        background: #061a2f;
        border-right: none;
    }
    [data-testid="stSidebar"] > div {
        background: linear-gradient(180deg, #061a2f 0%, #031426 100%);
        padding-top: 0.8rem;
    }
    [data-testid="stSidebar"] h4 {
        margin-top: 1.35rem;
        margin-bottom: 0.7rem;
        color: #8da2bd;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #d7e2f0;
    }
    [data-testid="stSidebar"] .stCaptionContainer {
        color: #9fb1c6;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        margin-bottom: 0.45rem;
        padding: 0.78rem 0.85rem;
        border-radius: 8px;
        border: 1px solid transparent;
        background: transparent;
        font-size: 0.9rem;
        font-weight: 650;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #2563eb;
        border-color: #3b82f6;
        color: #ffffff;
        box-shadow: 0 10px 22px rgba(37, 99, 235, 0.28);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) span,
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important;
    }
    .pipeline-status {
        position: static;
        width: auto;
        margin: 1.25rem 0 0.35rem;
        padding: 0.8rem 0.85rem;
        border-top: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 0;
        background: transparent;
    }
    .pipeline-status div {
        display: flex;
        align-items: center;
        gap: 0.42rem;
        color: #e2e8f0;
        font-size: 0.78rem;
        margin-bottom: 0.28rem;
        font-weight: 700;
    }
    .pipeline-status p {
        margin: 0.16rem 0;
        color: #9fb1c6;
        font-size: 0.7rem;
        font-weight: 500;
        line-height: 1.35;
    }
    .status-dot-mini {
        width: 0.42rem;
        height: 0.42rem;
        border-radius: 999px;
        background: #16a34a;
        box-shadow: none;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        border-radius: 8px;
        border-color: #e5e7eb;
        background: #ffffff;
        color: #111827;
        min-height: 2.85rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.035);
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="input"] input {
        color: #111827 !important;
        font-size: 0.82rem;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #334155;
        font-size: 0.68rem;
        font-weight: 760;
        line-height: 1;
        margin-bottom: 0.12rem;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="input"] > div {
        border-color: rgba(148, 163, 184, 0.28);
        background: #071f38;
        color: #e2e8f0;
        min-height: 2.55rem;
        box-shadow: none;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] span,
    [data-testid="stSidebar"] div[data-baseweb="input"] input {
        color: #e2e8f0 !important;
    }
    .refresh-spacer {
        height: 1.05rem;
    }
    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 2.85rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        color: #0f172a;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.035);
        font-size: 1.05rem;
        font-weight: 800;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #bfdbfe;
        color: #2563eb;
        background: #f8fbff;
    }
    .kpi-grid {
        display: grid;
        gap: 0.85rem;
        margin: 0.6rem 0 0.95rem;
    }
    .kpi-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        min-height: 118px;
        padding: 1rem 1.12rem;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.07);
        border-left: none;
    }
    .kpi-icon {
        display: grid;
        place-items: center;
        flex: 0 0 54px;
        width: 54px;
        height: 54px;
        border-radius: 999px;
        font-size: 1.2rem;
        font-weight: 800;
    }
    .kpi-card.volume .kpi-icon { background: #dbeafe; color: #2563eb; }
    .kpi-card.engagement .kpi-icon { background: #ede9fe; color: #6d28d9; }
    .kpi-card.sentiment .kpi-icon { background: #dcfce7; color: #16a34a; }
    .kpi-card.audience .kpi-icon { background: #d1fae5; color: #0f766e; }
    .kpi-card.content .kpi-icon { background: #ffedd5; color: #ea580c; }
    .kpi-card.quality .kpi-icon { background: #fee2e2; color: #dc2626; }
    .kpi-copy {
        min-width: 0;
        flex: 1;
    }
    .kpi-card-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.34rem;
    }
    .kpi-card-top > span:first-child {
        color: #111827;
        font-size: 0.8rem;
        font-weight: 720;
        letter-spacing: 0;
        text-transform: none;
    }
    .kpi-card-top > span:first-child::before {
        content: none;
    }
    .kpi-card strong {
        display: block;
        color: #111827;
        font-size: 1.75rem;
        font-weight: 760;
        letter-spacing: -0.025em;
        line-height: 1.1;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .kpi-card p {
        margin: 0.55rem 0 0;
        color: #6b7280;
        font-size: 0.72rem;
        line-height: 1.35;
    }
    .kpi-delta,
    .kpi-status,
    .kpi-id {
        flex-shrink: 0;
        padding: 0;
        border-radius: 0;
        font-size: 0.7rem;
        font-weight: 700;
        line-height: 1;
        background: transparent !important;
        border: none !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .kpi-delta.positive { color: #15803d; }
    .kpi-delta.negative { color: #b91c1c; }
    .kpi-delta.neutral,
    .kpi-status.neutral,
    .kpi-status.muted { color: #6b7280; }
    .kpi-status.fresh,
    .kpi-status.healthy { color: #15803d; }
    .kpi-status.stale,
    .kpi-status.warning { color: #a16207; }
    .kpi-id { color: #6b7280; }
    div[data-testid="stPlotlyChart"] {
        padding: 0.78rem;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stMarkdownContainer"] h3 {
        margin: 0.9rem 0 0.55rem;
        color: #111827;
        font-size: 1rem;
        line-height: 1.2;
        font-weight: 760;
        letter-spacing: -0.015em;
    }
    .section-title {margin: 1.2rem 0 0.55rem;}
    .section-title h2 {
        margin: 0;
        color: #111827;
        font-size: 1rem;
        letter-spacing: -0.015em;
        text-transform: none;
        font-weight: 700;
    }
    .section-title p {
        margin: 0.18rem 0 0;
        color: #6b7280;
        font-size: 0.78rem;
    }
    .insight-grid {display:none;}
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stMarkdownContainer"] p,
    .stCaptionContainer {
        color: #6b7280;
    }
    @media (max-width: 1100px) {
        section.page-header {flex-direction: column; align-items: flex-start;}
        .header-meta {width: 100%; text-align:left;}
        .kpi-grid {grid-template-columns: repeat(2, minmax(0, 1fr)) !important;}
        .pipeline-status {position: static; width: auto;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if tweets.empty:
    st.info("No tweet batches found yet. Run `python -m tweetpulse.synthetic_stream` to generate local data.")
    st.stop()

filtered_tweets, controls = build_sidebar_filters(tweets)

if filtered_tweets.empty:
    st.warning("No posts match the selected filters. Try widening the time window or selecting more topics.")
    st.stop()

total_posts = len(filtered_tweets)
average_engagement = filtered_tweets["engagement"].mean()
positive_rate = rate(filtered_tweets, "positive")
negative_rate = rate(filtered_tweets, "negative")
net_sentiment = positive_rate - negative_rate
recent_posts, previous_posts, recent_engagement, previous_engagement = latest_window_metrics(filtered_tweets)
topic_rank = filtered_tweets.groupby("topic", as_index=False).agg(
    posts=("tweet_id", "count"),
    engagement=("engagement", "sum"),
    avg_engagement=("engagement", "mean"),
).sort_values(str(controls["ranking_metric"]), ascending=False)
top_topic = topic_rank.iloc[0]["topic"] if not topic_rank.empty else "n/a"
top_topic_posts = int(topic_rank.iloc[0]["posts"]) if not topic_rank.empty else 0
top_topic_share = (top_topic_posts / total_posts) * 100 if total_posts else 0
newest_timestamp = filtered_tweets["created_at"].max()
latest_age = pd.Timestamp.now(tz="UTC") - newest_timestamp
freshness_status = "fresh" if latest_age <= pd.Timedelta(minutes=45) else "stale"
unique_authors = filtered_tweets["author"].nunique()
negative_posts = (filtered_tweets["sentiment"] == "negative").sum()
likes_total = filtered_tweets["likes"].sum() if "likes" in filtered_tweets else 0
reposts_total = filtered_tweets["reposts"].sum() if "reposts" in filtered_tweets else 0
replies_total = filtered_tweets["replies"].sum() if "replies" in filtered_tweets else 0
quotes_total = filtered_tweets["quotes"].sum() if "quotes" in filtered_tweets else None
total_engagement = filtered_tweets["engagement"].sum()
engagement_rate_proxy = (total_engagement / total_posts) if total_posts else 0
tweet_velocity = recent_posts / 60
virality_score = (reposts_total / total_posts) if total_posts else 0
sentiment_score_proxy = filtered_tweets["sentiment"].map(
    {"positive": 0.6, "neutral": 0.0, "negative": -0.6}
).fillna(0)
median_sentiment_score = sentiment_score_proxy.median()
neutral_rate = rate(filtered_tweets, "neutral")

filtered_tweets = filtered_tweets.assign(
    time_bucket=filtered_tweets["created_at"].dt.floor(str(controls["time_bucket"]))
)
trend = filtered_tweets.groupby("time_bucket", as_index=False).agg(
    posts=("tweet_id", "count"),
    engagement=("engagement", "sum"),
    avg_engagement=("engagement", "mean"),
    negative_posts=("sentiment", lambda values: (values == "negative").sum()),
)
hourly_sentiment = filtered_tweets.groupby(["hour", "sentiment"], as_index=False).size()
sentiment_mix = filtered_tweets.groupby("sentiment", as_index=False).size()
top_topic_names = topic_rank.head(int(controls["top_n"]))["topic"]
topic_sentiment = filtered_tweets[
    filtered_tweets["topic"].isin(top_topic_names)
].groupby(["topic", "sentiment"], as_index=False).size()
dominant_sentiment = sentiment_mix.sort_values("size", ascending=False).iloc[0]
peak_window = trend.sort_values("posts", ascending=False).iloc[0]
top_post = filtered_tweets.sort_values("engagement", ascending=False).iloc[0]

render_insight_cards(
    [
        ("Leading topic", top_topic, f"Ranked by {str(controls['ranking_label']).lower()}"),
        ("Topic concentration", f"{top_topic_share:.1f}%", f"{top_topic_posts} posts in top topic"),
        ("Dominant mood", dominant_sentiment["sentiment"], f"{int(dominant_sentiment['size'])} posts"),
        ("Peak window", f"{int(peak_window['posts'])} posts", f"{controls['trend_granularity']} bucket"),
        ("Top post engagement", metric_value(top_post["engagement"]), display_author(top_post["author"])),
    ]
)

ranking_metric = str(controls["ranking_metric"])
ranking_label = str(controls["ranking_label"]).lower()
top_topics_for_chart = topic_rank.head(int(controls["top_n"]))
table = filtered_tweets.sort_values("engagement", ascending=False)[
    ["created_at", "author", "topic", "sentiment", "engagement", "text"]
].head(int(controls["table_rows"]))
table = table.assign(
    author=table["author"].map(display_author),
    created_at=table["created_at"].dt.strftime("%b %d, %Y %I:%M %p"),
)

engagement_parts = pd.DataFrame(
    [
        {"type": "Likes", "value": likes_total},
        {"type": "Reposts", "value": reposts_total},
        {"type": "Replies", "value": replies_total},
    ]
).sort_values("value", ascending=True)
hourly_engagement = filtered_tweets.groupby("hour", as_index=False).agg(
    posts=("tweet_id", "count"),
    engagement=("engagement", "sum"),
)
hourly_engagement["engagement_per_post"] = (
    hourly_engagement["engagement"] / hourly_engagement["posts"].replace(0, pd.NA)
).fillna(0)

sentiment_pivot = hourly_sentiment.pivot_table(
    index="hour",
    columns="sentiment",
    values="size",
    aggfunc="sum",
    fill_value=0,
).reset_index()
for sentiment_name in ["positive", "neutral", "negative"]:
    if sentiment_name not in sentiment_pivot:
        sentiment_pivot[sentiment_name] = 0
sentiment_pivot["total"] = sentiment_pivot[["positive", "neutral", "negative"]].sum(axis=1)
for sentiment_name in ["positive", "neutral", "negative"]:
    sentiment_pivot[f"{sentiment_name}_pct"] = (
        sentiment_pivot[sentiment_name] / sentiment_pivot["total"].replace(0, pd.NA) * 100
    ).fillna(0)
sentiment_trend = sentiment_pivot.melt(
    id_vars="hour",
    value_vars=["positive_pct", "neutral_pct", "negative_pct"],
    var_name="sentiment",
    value_name="share",
)
sentiment_trend["sentiment"] = sentiment_trend["sentiment"].str.replace("_pct", "", regex=False)

author_rank = filtered_tweets.groupby("author", as_index=False).agg(
    posts=("tweet_id", "count"),
    engagement=("engagement", "sum"),
    avg_engagement=("engagement", "mean"),
).sort_values("engagement", ascending=False)
author_rank["author"] = author_rank["author"].map(display_author)

activity = filtered_tweets.assign(
    day=filtered_tweets["created_at"].dt.day_name().str[:3],
    hour_of_day=filtered_tweets["created_at"].dt.hour,
).groupby(["day", "hour_of_day"], as_index=False).agg(posts=("tweet_id", "count"))
avg_post_length = filtered_tweets["text"].fillna("").str.len().mean()
link_share_rate = filtered_tweets["text"].fillna("").str.contains("http", case=False, regex=False).mean() * 100
posts_per_author = total_posts / unique_authors if unique_authors else 0
alerts = classify_alerts(filtered_tweets, trend, latest_age, negative_rate)
selected_page = str(controls["page"])

if selected_page == "Overview":
    render_kpi_grid(
        [
            {"label": "Total Tweets", "value": compact_number(total_posts), "delta": recent_posts - previous_posts, "category": "volume", "icon": "💬", "help_text": "vs previous hour"},
            {
                "label": "Avg Engagement",
                "value": f"{decimal_value(engagement_rate_proxy)}/post",
                "category": "engagement",
                "icon": "👁",
                "help_text": "interactions per post",
            },
            {"label": "Engagements", "value": compact_number(total_engagement), "category": "audience", "icon": "👥", "help_text": "likes, replies, reposts"},
            {"label": "Velocity", "value": decimal_value(tweet_velocity, "/min"), "delta": (recent_posts - previous_posts) / 60, "delta_suffix": "/min", "category": "content", "icon": "↗", "help_text": "latest hour pace"},
            {"label": "Positive Sentiment", "value": decimal_value(positive_rate, "%"), "category": "sentiment", "icon": "☺", "help_text": "share of positive posts"},
        ],
        columns=5,
    )

    pulse_chart = px.area(
        trend,
        x="time_bucket",
        y="posts",
        title="Tweet Volume and Engagement Trend",
        labels={"time_bucket": "time", "posts": "posts"},
        color_discrete_sequence=[PRIMARY_BLUE],
        custom_data=["engagement", "avg_engagement", "negative_posts"],
    )
    pulse_chart.update_traces(
        fillcolor="rgba(37, 99, 235, 0.16)",
        line=dict(color=PRIMARY_BLUE, width=2),
        hovertemplate=(
            "<b>%{x|%b %d, %I:%M %p}</b><br>"
            "Posts: %{y:,}<br>"
            "Total engagement: %{customdata[0]:,.0f}<br>"
            "Avg engagement: %{customdata[1]:,.0f}<br>"
            "Negative posts: %{customdata[2]:,}<extra></extra>"
        )
    )

    topic_chart = px.bar(
        top_topics_for_chart.sort_values(ranking_metric),
        x=ranking_metric,
        y="topic",
        orientation="h",
        title="Top Topics by Engagement",
        labels={
            "engagement": "total engagement",
            "posts": "posts",
            "avg_engagement": "avg engagement/post",
            "topic": "topic",
        },
        color_discrete_sequence=[PRIMARY_BLUE],
        custom_data=["posts", "engagement", "avg_engagement"],
    )
    topic_chart.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"Ranked by {ranking_label}: "
            "%{x:,.0f}<br>"
            "Posts: %{customdata[0]:,}<br>"
            "Total engagement: %{customdata[1]:,.0f}<br>"
            "Avg engagement/post: %{customdata[2]:,.0f}<extra></extra>"
        )
    )
    sentiment_chart = px.pie(
        sentiment_mix,
        names="sentiment",
        values="size",
        hole=0.58,
        title="Sentiment Mix",
        color="sentiment",
        color_discrete_map=BRAND_COLORS,
    )
    sentiment_chart.update_traces(
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Posts: %{value:,}<br>Share: %{percent}<extra></extra>",
    )

    trend_col, topics_col, sentiment_col = st.columns([1.55, 1, 0.9])
    with trend_col:
        st.plotly_chart(style_chart(pulse_chart, height=360), use_container_width=True, config=CHART_CONFIG)
    with topics_col:
        st.plotly_chart(style_chart(topic_chart, height=360), use_container_width=True, config=CHART_CONFIG)
    with sentiment_col:
        st.plotly_chart(style_chart(sentiment_chart, height=360), use_container_width=True, config=CHART_CONFIG)

    attention = (
        filtered_tweets.groupby("topic", as_index=False)
        .agg(
            engagement=("engagement", "sum"),
            posts=("tweet_id", "count"),
            negative_posts=("sentiment", lambda values: (values == "negative").sum()),
        )
        .assign(negative_share=lambda frame: frame["negative_posts"] / frame["posts"].replace(0, pd.NA) * 100)
        .fillna(0)
        .sort_values(["negative_share", "engagement"], ascending=False)
        .head(6)
    )
    attention_table = attention.assign(
        negative_share=attention["negative_share"].map(lambda value: f"{value:.1f}%"),
        engagement=attention["engagement"].map(lambda value: f"{value:,.0f}"),
    )[["topic", "negative_share", "engagement"]]
    top_hashtags = top_topics_for_chart.assign(hashtag="#" + top_topics_for_chart["topic"].astype(str))
    feed_table = table.head(6).rename(
        columns={
            "created_at": "Created At",
            "topic": "Topic",
            "sentiment": "Sentiment",
            "engagement": "Engagement",
            "text": "Post",
        }
    )[["Created At", "Topic", "Sentiment", "Engagement", "Post"]]

    feed_col, hashtag_col, attention_col = st.columns([1.35, 0.95, 1])
    with feed_col:
        st.markdown("### High-Engagement Posts")
        st.dataframe(feed_table, hide_index=True, use_container_width=True)
    with hashtag_col:
        hashtag_chart = px.bar(
            top_hashtags.sort_values(ranking_metric),
            x="hashtag",
            y=ranking_metric,
            title="Top Hashtags",
            labels={"hashtag": "", ranking_metric: "engagement"},
            color_discrete_sequence=[PRIMARY_BLUE],
        )
        hashtag_chart.update_traces(hovertemplate="<b>%{x}</b><br>Engagement: %{y:,.0f}<extra></extra>")
        st.plotly_chart(style_chart(hashtag_chart, height=320), use_container_width=True, config=CHART_CONFIG)
    with attention_col:
        st.markdown("### Topics Needing Attention")
        st.dataframe(attention_table, hide_index=True, use_container_width=True)

if selected_page == "Engagement":
    render_kpi_grid(
        [
            {"label": "Total retweets", "value": compact_number(reposts_total), "category": "engagement", "kpi_id": "KPI-09", "help_text": "Adapted to Bluesky reposts."},
            {"label": "Total likes", "value": compact_number(likes_total), "category": "engagement", "kpi_id": "KPI-10"},
            {"label": "Total replies", "value": compact_number(replies_total), "category": "engagement", "kpi_id": "KPI-11"},
            {
                "label": "Total quote tweets",
                "value": compact_number(quotes_total) if quotes_total is not None else "Not collected",
                "status": "Not collected" if quotes_total is None else None,
                "category": "engagement",
                "kpi_id": "KPI-12",
                "help_text": "Quote count exists in X/Twitter metrics but not in this Bluesky payload.",
            },
        ],
        columns=4,
    )

    render_kpi_grid(
        [
            {"label": "Average reply depth", "value": "Not collected", "status": "Not collected", "category": "engagement", "kpi_id": "KPI-19", "help_text": "Requires thread/reply-level metadata."},
            {"label": "Max thread depth today", "value": "Not collected", "status": "Not collected", "category": "engagement", "kpi_id": "KPI-20", "help_text": "Requires conversation chain parsing."},
            {"label": "Virality score", "value": decimal_value(virality_score, "x"), "category": "engagement", "kpi_id": "KPI-06", "help_text": "Average reposts per post."},
        ],
        columns=3,
    )

    left, right = st.columns([1, 1.2])
    with left:
        engagement_chart = px.bar(
            engagement_parts,
            x="value",
            y="type",
            orientation="h",
            title="Engagement Breakdown",
            labels={"value": "interactions", "type": ""},
            color_discrete_sequence=[PRIMARY_BLUE],
        )
        engagement_chart.update_traces(
            hovertemplate="<b>%{y}</b><br>Interactions: %{x:,.0f}<extra></extra>"
        )
        st.plotly_chart(style_chart(engagement_chart, height=380), use_container_width=True, config=CHART_CONFIG)
    with right:
        peak_chart = px.bar(
            hourly_engagement,
            x="hour",
            y="engagement_per_post",
            title="Peak Engagement Windows",
            labels={"hour": "time", "engagement_per_post": "engagement/post"},
            color_discrete_sequence=[PRIMARY_BLUE],
            custom_data=["posts", "engagement"],
        )
        peak_chart.update_traces(
            hovertemplate=(
                "<b>%{x|%b %d, %I:%M %p}</b><br>"
                "Engagement/post: %{y:,.0f}<br>"
                "Posts: %{customdata[0]:,}<br>"
                "Total engagement: %{customdata[1]:,.0f}<extra></extra>"
            )
        )
        st.plotly_chart(style_chart(peak_chart, height=380), use_container_width=True, config=CHART_CONFIG)

if selected_page == "Sentiment":
    render_kpi_grid(
        [
            {
                "label": "Median sentiment score",
                "value": f"{median_sentiment_score:+.2f}",
                "category": "sentiment",
                "kpi_id": "KPI-13",
                "help_text": "Proxy score: positive=+0.6, neutral=0, negative=-0.6.",
            },
            {"label": "Positive sentiment", "value": decimal_value(positive_rate, "%"), "category": "sentiment", "kpi_id": "KPI-03"},
            {"label": "Neutral sentiment", "value": decimal_value(neutral_rate, "%"), "category": "sentiment", "kpi_id": "KPI-14"},
            {"label": "Negative sentiment", "value": decimal_value(negative_rate, "%"), "category": "sentiment", "kpi_id": "KPI-15"},
        ],
        columns=4,
    )

    left, right = st.columns([1, 1.35])
    with left:
        mix_chart = px.pie(
            sentiment_mix,
            names="sentiment",
            values="size",
            hole=0.55,
            title="Sentiment Mix",
            color="sentiment",
            color_discrete_map=BRAND_COLORS,
        )
        mix_chart.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Posts: %{value:,}<br>Share: %{percent}<extra></extra>",
        )
        st.plotly_chart(style_chart(mix_chart, height=380), use_container_width=True, config=CHART_CONFIG)
    with right:
        sentiment_chart = px.line(
            sentiment_trend,
            x="hour",
            y="share",
            color="sentiment",
            title="Sentiment Trend",
            labels={"hour": "time", "share": "share of posts (%)"},
            color_discrete_map=BRAND_COLORS,
        )
        sentiment_chart.update_traces(
            mode="lines+markers",
            hovertemplate="<b>%{x|%b %d, %I:%M %p}</b><br>Share: %{y:.1f}%<extra></extra>",
        )
        st.plotly_chart(style_chart(sentiment_chart, height=380), use_container_width=True, config=CHART_CONFIG)

    topic_sentiment_chart = px.bar(
        topic_sentiment,
        x="topic",
        y="size",
        color="sentiment",
        barmode="group",
        title="Topic Sentiment Breakdown",
        labels={"size": "posts"},
        color_discrete_map=BRAND_COLORS,
        custom_data=["sentiment"],
    )
    topic_sentiment_chart.update_traces(
        hovertemplate="<b>%{x}</b><br>Sentiment: %{customdata[0]}<br>Posts: %{y:,}<extra></extra>"
    )
    st.plotly_chart(style_chart(topic_sentiment_chart), use_container_width=True, config=CHART_CONFIG)

if selected_page == "Audience":
    render_kpi_grid(
        [
            {"label": "Unique authors", "value": compact_number(unique_authors), "category": "audience", "kpi_id": "KPI-04"},
            {"label": "Average tweet length", "value": f"{decimal_value(avg_post_length)} chars", "category": "content", "kpi_id": "KPI-16", "help_text": "Adapted to Bluesky post text length."},
            {"label": "Link share rate", "value": decimal_value(link_share_rate, "%"), "category": "content", "kpi_id": "KPI-17"},
            {"label": "Languages detected", "value": "Not collected", "status": "Not collected", "category": "audience", "kpi_id": "KPI-18", "help_text": "Requires a language field from the source payload."},
        ],
        columns=4,
    )

    render_kpi_grid(
        [
            {"label": "Posts / author", "value": decimal_value(posts_per_author), "category": "audience"},
            {"label": "Estimated reach", "value": "Not collected", "status": "Not collected", "category": "audience", "kpi_id": "KPI-07", "help_text": "Requires follower counts per author."},
        ],
        columns=2,
    )

    left, right = st.columns([1.15, 1])
    with left:
        heatmap = px.density_heatmap(
            activity,
            x="hour_of_day",
            y="day",
            z="posts",
            title="Activity Heatmap",
            labels={"hour_of_day": "hour of day", "day": "day", "posts": "posts"},
            color_continuous_scale="Blues",
        )
        heatmap.update_traces(
            hovertemplate="<b>%{y} %{x}:00</b><br>Posts: %{z:,}<extra></extra>"
        )
        st.plotly_chart(style_chart(heatmap, height=420), use_container_width=True, config=CHART_CONFIG)
    with right:
        author_chart = px.bar(
            author_rank.head(10).sort_values("engagement"),
            x="engagement",
            y="author",
            orientation="h",
            title="Top Authors by Engagement",
            labels={"engagement": "total engagement", "author": "author"},
            color_discrete_sequence=[PRIMARY_BLUE],
            custom_data=["posts", "avg_engagement"],
        )
        author_chart.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total engagement: %{x:,.0f}<br>"
                "Posts: %{customdata[0]:,}<br>"
                "Avg engagement/post: %{customdata[1]:,.0f}<extra></extra>"
            )
        )
        st.plotly_chart(style_chart(author_chart, height=420), use_container_width=True, config=CHART_CONFIG)

if selected_page == "Alerts & Feed":
    alert_counts = alerts["severity"].value_counts()
    render_kpi_grid(
        [
            {"label": "Critical", "value": metric_value(alert_counts.get("critical", 0))},
            {"label": "Warnings", "value": metric_value(alert_counts.get("warning", 0))},
            {"label": "Info", "value": metric_value(alert_counts.get("info", 0))},
            {"label": "Healthy checks", "value": metric_value(alert_counts.get("healthy", 0))},
        ],
        columns=4,
    )

    left, right = st.columns([0.9, 1.35])
    with left:
        alert_table = alerts.assign(timestamp=alerts["timestamp"].dt.strftime("%b %d, %I:%M %p"))
        st.dataframe(alert_table, hide_index=True, use_container_width=True)
    with right:
        st.markdown("#### Live Post Feed")
        st.dataframe(
            table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "created_at": "Created",
                "author": "Author",
                "topic": "Topic",
                "sentiment": "Sentiment",
                "engagement": st.column_config.NumberColumn("Engagement", format="%d"),
                "text": st.column_config.TextColumn("Post Text", width="large"),
            },
        )
