from __future__ import annotations

import base64
import html
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
LLM_PATH = OUTPUTS / "llm" / "social_posts_llm_classified.csv"
ENRICHED_PATH = OUTPUTS / "analysis" / "social_posts_enriched.csv"
MASTER_PATH = OUTPUTS / "social_posts_master.csv"
PROFILE_SUMMARY_PATH = OUTPUTS / "travel_pages_20260929T222511Z_social_summary.csv"
LOGO_PATH = ROOT / "assets" / "goods_unite_us_logo.png"

METRIC_COLS = ["likes", "comments", "replies", "shares", "reposts", "quotes"]
COLOR_RANGE = ["#2166C7", "#2F9E55", "#8B5ED7", "#F59F00", "#F2846B", "#43AA8B"]
STATUS_COLORS = ["#43AA8B", "#8B5ED7", "#F2846B", "#3B82C4"]
REPORT_BLUE = "#0F4FA8"
REPORT_RED = "#FF4D4D"


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("No social post dataset found.")


def label(value: object) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return "Unknown"
    return str(value).replace("_", " ").strip().title()


def short_text(value: object, limit: int = 240) -> str:
    if pd.isna(value):
        return ""
    text = " ".join(str(value).split())
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def display_value(value: object, fallback: str = "Not available") -> str:
    if pd.isna(value) or str(value).strip() == "":
        return fallback
    return str(value)


def parse_count(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KkMm])?", text)
    if not match:
        return None
    number = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    return number


@st.cache_data
def load_posts() -> pd.DataFrame:
    source_path = first_existing([LLM_PATH, ENRICHED_PATH, MASTER_PATH])
    df = pd.read_csv(source_path)
    df.attrs["source_path"] = str(source_path)

    for col in [*METRIC_COLS, "total_engagements", "platform_percentile"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "published_at" in df.columns:
        df["published_at_dt"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
        df["published_date"] = df["published_at_dt"].dt.date
        df["post_month"] = df["published_at_dt"].dt.strftime("%Y-%m")
    else:
        df["published_at_dt"] = pd.NaT
        df["published_date"] = pd.NA
        df["post_month"] = ""

    text = df["post_text"] if "post_text" in df.columns else pd.Series("", index=df.index)
    df["post"] = text.apply(short_text)
    df["post_key"] = df.get("platform", "").astype(str) + ":" + df.get("post_id", "").astype(str)
    df["has_metrics"] = df["total_engagements"].notna() if "total_engagements" in df.columns else False

    if "llm_content_lane" not in df.columns and "content_type" in df.columns:
        df["llm_content_lane"] = df["content_type"]
    if "llm_cta_type" not in df.columns and "cta_type" in df.columns:
        df["llm_cta_type"] = df["cta_type"]
    if "llm_emotional_frame" not in df.columns:
        df["llm_emotional_frame"] = "unclassified"

    df["platform_label"] = df.get("platform", pd.Series("", index=df.index)).apply(label)
    df["content_type"] = df.get("llm_content_lane", pd.Series("", index=df.index)).apply(label)
    df["framing"] = df.get("llm_emotional_frame", pd.Series("", index=df.index)).apply(label)
    df["cta_style"] = df.get("llm_cta_type", pd.Series("", index=df.index)).apply(label)
    return df


@st.cache_data
def load_profiles() -> pd.DataFrame:
    if not PROFILE_SUMMARY_PATH.exists():
        return pd.DataFrame(
            columns=[
                "platform",
                "platform_label",
                "url",
                "status",
                "title",
                "followers",
                "following",
                "posts_or_threads",
                "bio_or_description",
            ]
        )
    profiles = pd.read_csv(PROFILE_SUMMARY_PATH)
    profiles["platform_label"] = profiles.get("platform", pd.Series("", index=profiles.index)).apply(label)
    for col in ["followers", "following", "posts_or_threads", "bio_or_description", "url", "status", "title"]:
        if col not in profiles.columns:
            profiles[col] = ""
    profiles["followers_count"] = profiles["followers"].apply(parse_count)
    profiles["following_count"] = profiles["following"].apply(parse_count)
    profiles["profile_posts_count"] = profiles["posts_or_threads"].apply(parse_count)
    return profiles


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f5f6f8; color: #202124; }
        .block-container {
          max-width: 100%;
          padding: 2.75rem 1.15rem 2rem 1.15rem;
        }
        h1, h2, h3 { letter-spacing: 0; }
        h1 { font-size: 1.8rem; margin-bottom: .15rem; }
        h2, h3 {
          color: #343a40;
          font-weight: 800;
          font-size: 1.12rem;
          margin: 1.55rem 0 .5rem 0;
        }
        div[data-testid="stVerticalBlock"] { gap: .75rem; }
        div[data-testid="column"] { min-width: 0; }
        section[data-testid="stSidebar"] {
          background: #f7f8fa;
          border-right: 1px solid #d8dde3;
        }
        section[data-testid="stSidebar"] > div {
          padding-top: 0 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
          gap: .35rem;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
          color: #0F4FA8;
          font-size: 1.1rem;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
          color: #59656f;
        }
        .report-header {
          background: transparent;
          border: 0;
          box-shadow: none;
          padding: 10px 0 24px 0;
          margin: 0 0 10px 0;
          display: grid;
          grid-template-columns: 102px minmax(0, 1fr) 455px;
          gap: 2px;
          align-items: center;
          min-height: 120px;
          overflow: visible;
        }
        .logo-tile {
          background: transparent;
          border: 0;
          width: 100px;
          height: 86px;
          display: flex;
          align-items: center;
          justify-content: flex-start;
          overflow: hidden;
        }
        .logo-tile img {
          max-width: 100%;
          max-height: 100%;
          object-fit: contain;
        }
        .report-title {
          color: #202124;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          font-size: 1.55rem;
          font-weight: 800;
          margin: 0 0 8px 0;
          line-height: 1.15;
          overflow: visible;
        }
        .report-subtitle {
          color: #555b62;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          font-size: .7rem;
          font-weight: 400;
          line-height: 1.35;
          max-width: 920px;
        }
        .date-range-widget {
          padding: 0;
          color: #0F4FA8;
          font-weight: 800;
          font-size: .8rem;
        }
        .date-range-top {
          margin-bottom: 2px;
        }
        .date-range-labels {
          display: flex;
          justify-content: space-between;
          color: #0F4FA8;
          font-size: .82rem;
          font-weight: 800;
          margin-bottom: 8px;
        }
        .date-slider {
          position: relative;
          height: 16px;
        }
        .date-slider::before {
          content: "";
          position: absolute;
          left: 8px;
          right: 8px;
          top: 6px;
          height: 4px;
          border-radius: 999px;
          background: #FF4D4D;
        }
        .date-slider::after {
          content: none;
        }
        .date-knob {
          position: absolute;
          top: 1px;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #FF4D4D;
        }
        .date-knob.start { left: 2px; }
        .date-knob.end { right: 2px; }
        .chart-panel {
          border: 1px solid #dcdfe3;
          border-radius: 10px;
          background: #ffffff;
          padding: 8px 10px 2px 10px;
          margin-bottom: 18px;
        }
        .insight-box {
          background: #f7f9fa;
          border: 1px solid #d8dde3;
          border-radius: 5px;
          padding: 14px 16px;
          margin-bottom: 10px;
        }
        .insight-box strong { color: #172026; }
        .small-note { color: #62707a; font-size: .9rem; }
        div[data-baseweb="tag"] {
          background-color: #0F4FA8 !important;
        }
        div[data-baseweb="tag"] span {
          color: #ffffff !important;
        }
        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 24px;
          margin: 0 0 26px 0;
        }
        .kpi-card {
          position: relative;
          background: #ffffff;
          border: 1px solid #dcdfe3;
          border-radius: 10px;
          min-height: 102px;
          padding: 16px 28px 13px 28px;
          overflow: hidden;
        }
        .kpi-card::before {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 5px;
        }
        .kpi-blue::before { background: #1F77E8; }
        .kpi-green::before { background: #2F9E55; }
        .kpi-purple::before { background: #9B4DFF; }
        .kpi-orange::before { background: #F59F00; }
        .kpi-card-subtitle {
          color: #5f666d;
          font-size: .79rem;
          font-weight: 500;
          margin-top: 11px;
        }
        .kpi-label {
          color: #3a3f45;
          font-size: .94rem;
          font-weight: 700;
          line-height: 1.2;
          margin-bottom: 14px;
        }
        .kpi-value {
          color: #202124;
          font-size: 1.85rem;
          line-height: 1;
          font-weight: 800;
        }
        .coverage-stat {
          display: flex;
          align-items: baseline;
          gap: 10px;
          margin: 4px 0 2px 0;
        }
        .coverage-value {
          color: #303030;
          font-size: 1.65rem;
          font-weight: 600;
          line-height: 1;
        }
        .coverage-label {
          color: #59656f;
          font-size: .9rem;
          font-weight: 600;
        }
        .profile-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 18px;
          margin: 4px 0 20px 0;
        }
        .profile-card {
          background: #ffffff;
          border: 1px solid #dcdfe3;
          border-radius: 10px;
          padding: 18px 20px;
          min-height: 132px;
        }
        .profile-platform {
          color: #202124;
          font-size: 1.05rem;
          font-weight: 800;
          margin-bottom: 10px;
        }
        .profile-stat {
          color: #59616a;
          font-size: .82rem;
          line-height: 1.45;
          margin: 3px 0;
        }
        .profile-stat strong {
          color: #202124;
        }
        .profile-note {
          color: #59616a;
          font-size: .82rem;
          margin: 2px 0 16px 0;
        }
        @media (max-width: 1100px) {
          .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .profile-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 900px) {
          .block-container { padding: 1rem; }
          .report-header {
            grid-template-columns: 1fr;
            min-height: auto;
          }
          .date-box { text-align: left; }
          .kpi-grid { grid-template-columns: 1fr; }
          .profile-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def fmt_number(value: float | int | None, decimals: int = 0) -> str:
    if pd.isna(value):
        return "n/a"
    if decimals:
        return f"{value:,.{decimals}f}"
    return f"{value:,.0f}"


def filtered_posts(df: pd.DataFrame) -> pd.DataFrame:
    platform_options = sorted(df["platform_label"].dropna().unique())
    working = df.copy()
    if "data_quality" in working.columns:
        working = working[working["data_quality"].ne("out_of_scope")]

    dates = working["published_at_dt"].dropna()
    if not dates.empty:
        min_date = dates.min().date()
        max_date = dates.max().date()
        selected_dates = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        selected_dates = None

    selected_platforms = st.sidebar.multiselect("Platform", platform_options, default=platform_options)

    filtered = working.copy()
    if selected_dates and isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start, end = selected_dates
        in_range = (filtered["published_at_dt"].dt.date >= start) & (filtered["published_at_dt"].dt.date <= end)
        missing_date = filtered["published_at_dt"].isna()
        filtered = filtered[
            in_range | missing_date
        ]
    if selected_platforms:
        filtered = filtered[filtered["platform_label"].isin(selected_platforms)]

    st.sidebar.caption(f"{len(filtered):,} posts selected")

    return filtered


def date_range_label(df: pd.DataFrame) -> str:
    dates = df["published_at_dt"].dropna() if "published_at_dt" in df.columns else pd.Series([], dtype="datetime64[ns]")
    if dates.empty:
        return "Date range unavailable"
    start = dates.min().strftime("%-d %b %Y")
    end = dates.max().strftime("%-d %b %Y")
    return f"{start} - {end}"


def date_range_month_labels(df: pd.DataFrame) -> tuple[str, str]:
    dates = df["published_at_dt"].dropna() if "published_at_dt" in df.columns else pd.Series([], dtype="datetime64[ns]")
    if dates.empty:
        return "Start", "End"
    return dates.min().strftime("%b %Y"), dates.max().strftime("%b %Y")


def report_header(df: pd.DataFrame) -> None:
    logo_src = logo_data_uri()
    start_month, end_month = date_range_month_labels(df)
    st.markdown(
        f"""
        <div class="report-header">
          <div class="logo-tile">{logo_src}</div>
          <div>
            <div class="report-title">Social Content Performance Dashboard</div>
            <div class="report-subtitle">This report gives an overview of social content engagement, platform coverage, and post activity trends across the selected time period.</div>
          </div>
          <div class="date-range-widget">
            <div class="date-range-top">Date range</div>
            <div class="date-range-labels"><span>{start_month}</span><span>{end_month}</span></div>
            <div class="date-slider"><span class="date-knob start"></span><span class="date-knob end"></span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return "GOODS<br>UNITE US"
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{encoded}" alt="Goods Unite Us logo">'


def section_title(text: str) -> None:
    st.markdown(f"### {text}")


def chart_panel(chart: alt.Chart) -> None:
    st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def platform_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby("platform_label", dropna=False)
        .agg(
            posts=("post_key", "count"),
            posts_with_metrics=("has_metrics", "sum"),
            total_engagement=("total_engagements", "sum"),
            avg_engagement=("total_engagements", "mean"),
            avg_performance=("platform_percentile", "mean"),
        )
        .reset_index()
        .rename(columns={"platform_label": "Platform"})
        .round({"avg_engagement": 1, "avg_performance": 1})
    )


def pattern_summary(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in df.columns or df.empty:
        return pd.DataFrame()
    return (
        df.groupby(column, dropna=False)
        .agg(
            posts=("post_key", "count"),
            avg_performance=("platform_percentile", "mean"),
            avg_engagement=("total_engagements", "mean"),
        )
        .reset_index()
        .dropna(subset=["avg_performance"])
        .sort_values("avg_performance", ascending=False)
        .round({"avg_performance": 1, "avg_engagement": 1})
    )


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "post_month" not in df.columns:
        return pd.DataFrame()
    monthly = (
        df[df["post_month"].fillna("").ne("")]
        .groupby(["post_month", "platform_label"], dropna=False)
        .agg(
            posts=("post_key", "count"),
            total_engagement=("total_engagements", "sum"),
            avg_performance=("platform_percentile", "mean"),
        )
        .reset_index()
        .round({"avg_performance": 1})
    )
    return monthly


def engagement_mix(df: pd.DataFrame) -> pd.DataFrame:
    available_metrics = [col for col in METRIC_COLS if col in df.columns]
    if not available_metrics or df.empty:
        return pd.DataFrame()
    mix = df.melt(
        id_vars=["platform_label"],
        value_vars=available_metrics,
        var_name="Metric",
        value_name="Count",
    )
    mix["Metric"] = mix["Metric"].apply(label)
    mix["Count"] = pd.to_numeric(mix["Count"], errors="coerce").fillna(0)
    return (
        mix.groupby(["platform_label", "Metric"], dropna=False)
        .agg(Count=("Count", "sum"))
        .reset_index()
        .query("Count > 0")
    )


def vertical_bar(df: pd.DataFrame, x: str, y: str, color: str | None = None, height: int = 300) -> alt.Chart:
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(x, sort="-y", axis=alt.Axis(labelLimit=160), title=None),
            y=alt.Y(y, title=None),
            tooltip=list(df.columns),
        )
        .properties(height=height)
    )
    if color:
        chart = chart.encode(color=alt.Color(color, scale=alt.Scale(range=COLOR_RANGE), legend=None))
    else:
        chart = chart.encode(color=alt.value("#2F6F73"))
    return chart


def horizontal_bar(df: pd.DataFrame, label_col: str, value_col: str, height: int = 300, value_title: str = "Value") -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#2F6F73")
        .encode(
            x=alt.X(f"{value_col}:Q", title=value_title),
            y=alt.Y(f"{label_col}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=list(df.columns),
        )
        .properties(height=height)
    )


def trend_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("post_month:N", title="Month", sort=list(sorted(df["post_month"].dropna().unique()))),
            y=alt.Y("total_engagement:Q", title="Total engagement"),
            color=alt.Color("platform_label:N", title="Platform", scale=alt.Scale(range=COLOR_RANGE)),
            tooltip=["post_month", "platform_label", "posts", "total_engagement", "avg_performance"],
        )
        .properties(height=300)
    )


def engagement_mix_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("platform_label:N", title=None),
            y=alt.Y("Count:Q", title="Engagement actions"),
            color=alt.Color("Metric:N", scale=alt.Scale(range=COLOR_RANGE)),
            tooltip=["platform_label", "Metric", "Count"],
        )
        .properties(height=300)
    )


def performance_distribution_chart(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df.dropna(subset=["platform_percentile"]))
        .mark_boxplot(size=42, color="#2F6F73")
        .encode(
            x=alt.X("platform_label:N", title=None),
            y=alt.Y("platform_percentile:Q", title="Performance percentile", scale=alt.Scale(domain=[0, 100])),
            tooltip=["platform_label", "platform_percentile"],
        )
        .properties(height=300)
    )


def content_heatmap(df: pd.DataFrame) -> alt.Chart:
    heatmap = (
        df.dropna(subset=["platform_percentile"])
        .groupby(["platform_label", "content_type"], dropna=False)
        .agg(
            posts=("post_key", "count"),
            avg_performance=("platform_percentile", "mean"),
        )
        .reset_index()
        .round({"avg_performance": 1})
    )
    return (
        alt.Chart(heatmap)
        .mark_rect()
        .encode(
            x=alt.X("platform_label:N", title=None),
            y=alt.Y("content_type:N", title=None, sort="-x", axis=alt.Axis(labelLimit=220)),
            color=alt.Color("avg_performance:Q", title="Avg performance", scale=alt.Scale(scheme="tealblues", domain=[0, 100])),
            tooltip=["platform_label", "content_type", "posts", "avg_performance"],
        )
        .properties(height=360)
    )


def content_mix_chart(df: pd.DataFrame) -> alt.Chart:
    mix = (
        df.groupby("content_type", dropna=False)
        .agg(posts=("post_key", "count"))
        .reset_index()
        .sort_values("posts", ascending=False)
    )
    return (
        alt.Chart(mix.head(8))
        .mark_arc(innerRadius=70, outerRadius=130, stroke="#f8f8f8", strokeWidth=2)
        .encode(
            theta=alt.Theta("posts:Q"),
            color=alt.Color("content_type:N", title="Content type", scale=alt.Scale(range=COLOR_RANGE)),
            tooltip=["content_type", "posts"],
        )
        .properties(height=330)
    )


def collected_posts_chart(df: pd.DataFrame) -> alt.Chart:
    if df.empty:
        return alt.Chart(pd.DataFrame({"Platform": [], "posts": [], "with_metrics": []})).mark_bar()
    counts = (
        df.groupby("platform_label", dropna=False)
        .agg(posts=("post_key", "count"), with_metrics=("has_metrics", "sum"))
        .reset_index()
        .rename(columns={"platform_label": "Platform"})
    )
    return (
        alt.Chart(counts)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Platform:N", title=None, sort="-y"),
            y=alt.Y("posts:Q", title="Posts collected"),
            color=alt.Color("Platform:N", scale=alt.Scale(range=COLOR_RANGE), legend=None),
            tooltip=["Platform", "posts", "with_metrics"],
        )
        .properties(height=260)
    )


def average_engagement_by_platform_chart(df: pd.DataFrame) -> alt.Chart:
    scored = df[df["has_metrics"]].copy()
    if scored.empty:
        chart_data = pd.DataFrame({"Platform": [], "avg_engagement": [], "posts": []})
    else:
        chart_data = (
            scored.groupby("platform_label", dropna=False)
            .agg(avg_engagement=("total_engagements", "mean"), posts=("post_key", "count"))
            .reset_index()
            .rename(columns={"platform_label": "Platform"})
            .round({"avg_engagement": 1})
            .sort_values("avg_engagement", ascending=False)
        )
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Platform:N", title=None, sort="-y", axis=alt.Axis(labelAngle=-45, labelColor="#7c8494")),
            y=alt.Y("avg_engagement:Q", title="Avg engagement per post", axis=alt.Axis(labelColor="#7c8494", titleColor="#7c8494")),
            color=alt.Color("Platform:N", scale=alt.Scale(range=COLOR_RANGE), legend=None),
            tooltip=["Platform", "avg_engagement", "posts"],
        )
        .properties(height=285)
    )


def engagement_coverage(df: pd.DataFrame) -> tuple[int, int, float]:
    total_posts = len(df)
    posts_with_metrics = int(df["has_metrics"].sum()) if "has_metrics" in df.columns and not df.empty else 0
    coverage_rate = posts_with_metrics / total_posts if total_posts else 0
    return total_posts, posts_with_metrics, coverage_rate


def engagement_coverage_donut(df: pd.DataFrame) -> alt.Chart:
    total_posts, posts_with_metrics, _ = engagement_coverage(df)
    missing_metrics = max(total_posts - posts_with_metrics, 0)
    coverage = pd.DataFrame(
        [
            {"Status": "With engagement data", "Posts": posts_with_metrics},
            {"Status": "Missing engagement data", "Posts": missing_metrics},
        ]
    )
    coverage = coverage[coverage["Posts"].gt(0)]
    if coverage.empty:
        coverage = pd.DataFrame([{"Status": "No selected posts", "Posts": 1}])

    return (
        alt.Chart(coverage)
        .mark_arc(innerRadius=72, outerRadius=125, stroke="#ffffff", strokeWidth=4)
        .encode(
            theta=alt.Theta("Posts:Q"),
            color=alt.Color(
                "Status:N",
                title=None,
                scale=alt.Scale(range=STATUS_COLORS),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=["Status", "Posts"],
        )
        .properties(height=260)
    )


def posts_by_platform_donut(df: pd.DataFrame) -> alt.Chart:
    if df.empty:
        chart_data = pd.DataFrame([{"Platform": "No selected posts", "Posts": 1}])
        total_posts = 0
    else:
        chart_data = (
            df.groupby("platform_label", dropna=False)
            .agg(Posts=("post_key", "count"))
            .reset_index()
            .rename(columns={"platform_label": "Platform"})
            .sort_values("Posts", ascending=False)
        )
        total_posts = int(chart_data["Posts"].sum())

    donut = (
        alt.Chart(chart_data)
        .mark_arc(innerRadius=86, outerRadius=150, stroke="#ffffff", strokeWidth=3)
        .encode(
            theta=alt.Theta("Posts:Q"),
            color=alt.Color("Platform:N", title=None, scale=alt.Scale(range=STATUS_COLORS), legend=alt.Legend(orient="right")),
            tooltip=["Platform", "Posts"],
        )
    )
    center = (
        alt.Chart(pd.DataFrame([{"label": f"{total_posts:,}\nTotal"}]))
        .mark_text(align="center", baseline="middle", fontSize=17, fontWeight=800, color="#1f2937", lineBreak="\n")
        .encode(text="label:N")
    )
    return (donut + center).properties(height=430)


def monthly_engagement_trends_chart(df: pd.DataFrame) -> alt.Chart:
    chart_data = (
        df[df["post_month"].fillna("").ne("") & df["has_metrics"]]
        .groupby(["post_month", "platform_label"], dropna=False)
        .agg(total_engagement=("total_engagements", "sum"))
        .reset_index()
        .sort_values("post_month")
    )
    if chart_data.empty:
        chart_data = pd.DataFrame({"post_month": [], "platform_label": [], "total_engagement": []})

    month_order = list(sorted(chart_data["post_month"].dropna().unique()))
    return (
        alt.Chart(chart_data)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=70), strokeWidth=3)
        .encode(
            x=alt.X(
                "post_month:N",
                title=None,
                sort=month_order,
                axis=alt.Axis(labelAngle=-35, labelColor="#7c8494", grid=False),
            ),
            y=alt.Y(
                "total_engagement:Q",
                title="Engagement",
                axis=alt.Axis(labelColor="#7c8494", titleColor="#7c8494"),
            ),
            color=alt.Color("platform_label:N", title=None, scale=alt.Scale(range=COLOR_RANGE), legend=alt.Legend(orient="top")),
            tooltip=["post_month", "platform_label", "total_engagement"],
        )
        .properties(height=430)
    )


def monthly_post_volume_chart(df: pd.DataFrame) -> alt.Chart:
    if df.empty or "post_month" not in df.columns:
        return alt.Chart(pd.DataFrame({"post_month": [], "platform_label": [], "posts": []})).mark_bar()
    volume = (
        df[df["post_month"].fillna("").ne("")]
        .groupby(["post_month", "platform_label"], dropna=False)
        .agg(posts=("post_key", "count"))
        .reset_index()
    )
    return (
        alt.Chart(volume)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("post_month:N", title="Month", sort=list(sorted(volume["post_month"].dropna().unique()))),
            y=alt.Y("posts:Q", title="Posts collected"),
            color=alt.Color("platform_label:N", title="Platform", scale=alt.Scale(range=COLOR_RANGE)),
            tooltip=["post_month", "platform_label", "posts"],
        )
        .properties(height=285)
    )


def post_scatter(df: pd.DataFrame) -> alt.Chart:
    scored = df.dropna(subset=["platform_percentile", "total_engagements"])
    return (
        alt.Chart(scored)
        .mark_circle(size=90, opacity=0.78)
        .encode(
            x=alt.X("total_engagements:Q", title="Engagement"),
            y=alt.Y("platform_percentile:Q", title="Performance percentile", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("platform_label:N", title="Platform", scale=alt.Scale(range=COLOR_RANGE)),
            tooltip=["platform_label", "content_type", "total_engagements", "platform_percentile", "post"],
        )
        .properties(height=360)
    )


def report_table(df: pd.DataFrame, columns: list[str], height: int = 390) -> None:
    available = [col for col in columns if col in df.columns]
    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        height=height,
        column_config={
            "platform_label": st.column_config.TextColumn("Platform", width="small"),
            "post": st.column_config.TextColumn("Post", width="large"),
            "content_type": st.column_config.TextColumn("Content type"),
            "framing": st.column_config.TextColumn("Framing"),
            "total_engagements": st.column_config.NumberColumn("Engagement", format="%.0f"),
            "platform_percentile": st.column_config.ProgressColumn("Performance", min_value=0, max_value=100, format="%.0f"),
            "llm_repurpose_recommendation": st.column_config.TextColumn("Suggested next step", width="large"),
            "post_url": st.column_config.LinkColumn("Link"),
        },
    )


def best_available(summary: pd.DataFrame, metric: str) -> pd.Series | None:
    if summary.empty or metric not in summary.columns or not summary[metric].notna().any():
        return None
    return summary.sort_values(metric, ascending=False).iloc[0]


def executive_summary(df: pd.DataFrame) -> None:
    scored = df[df["has_metrics"]]
    strong = scored[scored["platform_percentile"].ge(75)] if "platform_percentile" in scored.columns else scored.iloc[0:0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Posts reviewed", fmt_number(len(df)))
    c2.metric("Posts with metrics", fmt_number(len(scored)))
    c3.metric("Total engagement", fmt_number(scored["total_engagements"].sum() if not scored.empty else None))
    c4.metric("Strong posts", fmt_number(len(strong)))

    platforms = platform_summary(df)
    content = pattern_summary(scored, "content_type")
    framing = pattern_summary(scored, "framing")

    best_platform = best_available(platforms, "avg_engagement")
    best_content = best_available(content, "avg_performance")
    best_frame = best_available(framing, "avg_performance")

    st.subheader("Executive Takeaways")
    col1, col2, col3 = st.columns(3)
    with col1:
        text = "Need more native metrics before comparing platforms."
        if best_platform is not None:
            text = f"{best_platform['Platform']} has the highest average engagement among measured platforms."
        st.markdown(f"<div class='insight-box'><strong>Platform signal</strong><br>{text}</div>", unsafe_allow_html=True)
    with col2:
        text = "No measured content pattern yet."
        if best_content is not None:
            text = f"{best_content['content_type']} is the strongest measured content type."
        st.markdown(f"<div class='insight-box'><strong>Content signal</strong><br>{text}</div>", unsafe_allow_html=True)
    with col3:
        text = "No measured framing pattern yet."
        if best_frame is not None:
            text = f"{best_frame['framing']} framing is associated with stronger performance."
        st.markdown(f"<div class='insight-box'><strong>Creative signal</strong><br>{text}</div>", unsafe_allow_html=True)

    st.subheader("Recommended Focus")
    st.write("- Reuse top-performing post formats on the platforms where they already show traction.")
    st.write("- Turn strong content types into repeatable templates instead of one-off posts.")
    st.write("- Add native analytics exports next, especially reach, saves, shares, views, clicks, and profile actions.")

    st.subheader("Engagement Trend")
    monthly = monthly_summary(scored)
    if monthly.empty:
        st.info("Trend charts will appear once dated posts with metrics are available.")
    else:
        st.altair_chart(trend_chart(monthly), use_container_width=True)


def platform_performance(df: pd.DataFrame) -> None:
    summary = platform_summary(df)
    if summary.empty:
        st.info("No platform data available.")
        return

    left, right = st.columns(2)
    with left:
        st.subheader("Average Engagement")
        measured = summary.dropna(subset=["avg_engagement"])
        if measured.empty:
            st.info("No engagement metrics available for the selected posts.")
        else:
            st.altair_chart(vertical_bar(measured, "Platform:N", "avg_engagement:Q", "Platform:N"), use_container_width=True)
    with right:
        st.subheader("Average Performance")
        measured = summary.dropna(subset=["avg_performance"])
        if measured.empty:
            st.info("No normalized performance score available for the selected posts.")
        else:
            st.altair_chart(vertical_bar(measured, "Platform:N", "avg_performance:Q", "Platform:N"), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Engagement Mix")
        mix = engagement_mix(df[df["has_metrics"]])
        if mix.empty:
            st.info("No engagement action breakdown available.")
        else:
            st.altair_chart(engagement_mix_chart(mix), use_container_width=True)
    with right:
        st.subheader("Performance Spread")
        measured_posts = df.dropna(subset=["platform_percentile"])
        if measured_posts.empty:
            st.info("No post performance distribution available.")
        else:
            st.altair_chart(performance_distribution_chart(measured_posts), use_container_width=True)

    st.subheader("Platform Detail")
    st.dataframe(
        summary.rename(
            columns={
                "posts": "Posts collected",
                "posts_with_metrics": "Posts with metrics",
                "total_engagement": "Total engagement",
                "avg_engagement": "Avg engagement",
                "avg_performance": "Avg performance",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def content_strategy(df: pd.DataFrame) -> None:
    scored = df[df["has_metrics"]]

    st.subheader("Which Content Patterns Are Working?")
    content = pattern_summary(scored, "content_type")
    if content.empty:
        st.info("Content pattern performance will appear once more posts have metrics.")
    else:
        st.altair_chart(horizontal_bar(content.head(8), "content_type", "avg_performance", 340), use_container_width=True)

    st.subheader("Content Performance By Platform")
    if scored.dropna(subset=["platform_percentile"]).empty:
        st.info("Platform-by-content chart will appear once measured posts are available.")
    else:
        st.altair_chart(content_heatmap(scored), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Framing")
        framing = pattern_summary(scored, "framing")
        if not framing.empty:
            st.altair_chart(horizontal_bar(framing.head(6), "framing", "avg_performance", 260), use_container_width=True)
    with right:
        st.subheader("CTA Style")
        ctas = pattern_summary(scored, "cta_style")
        if not ctas.empty:
            st.altair_chart(horizontal_bar(ctas.head(6), "cta_style", "avg_performance", 260), use_container_width=True)

    st.subheader("How To Use This")
    st.write("- Prioritize content types near the top of the chart for the next publishing cycle.")
    st.write("- For weaker formats, change the hook, visual, or CTA before increasing volume.")
    st.write("- Compare performance within each platform rather than judging raw engagement across platforms.")


def post_review(df: pd.DataFrame) -> None:
    scored = df.dropna(subset=["platform_percentile"])
    if scored.empty:
        st.info("Post-level review will appear once performance metrics are available.")
        return

    st.subheader("Post Performance Map")
    st.altair_chart(post_scatter(scored), use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Repurpose These")
        winners = scored.sort_values("platform_percentile", ascending=False).head(12)
        report_table(winners, ["platform_label", "post", "content_type", "total_engagements", "platform_percentile", "post_url"], 430)
    with right:
        st.subheader("Improve These")
        weak = scored.sort_values("platform_percentile", ascending=True).head(12)
        report_table(weak, ["platform_label", "post", "content_type", "total_engagements", "platform_percentile", "post_url"], 430)

    if "llm_repurpose_recommendation" in df.columns:
        st.subheader("Suggested Next Steps")
        recs = (
            scored.sort_values("platform_percentile", ascending=False)
            [["platform_label", "post", "llm_repurpose_recommendation", "post_url"]]
            .head(10)
        )
        report_table(recs, ["platform_label", "post", "llm_repurpose_recommendation", "post_url"], 360)


def data_quality(df: pd.DataFrame) -> None:
    st.subheader("What The Report Can Answer")
    st.write("- Which collected posts performed better or worse within their own platform.")
    st.write("- Which content types, frames, and CTAs are associated with stronger measured posts.")
    st.write("- Which posts should be reused, rewritten, or tested again.")

    st.subheader("What Still Needs Native Analytics")
    st.write(
        "For a complete read, connect native exports or APIs for reach, saves, shares, views, clicks, profile visits, follows, "
        "watch time, and completion rate."
    )

    summary = platform_summary(df)
    if summary.empty:
        st.info("No platform coverage available for the selected filters.")
    else:
        coverage = summary[["Platform", "posts", "posts_with_metrics"]].rename(
            columns={"posts": "Posts collected", "posts_with_metrics": "Posts with performance metrics"}
        )
        st.dataframe(coverage, use_container_width=True, hide_index=True)

    missing = df[~df["has_metrics"]]
    if not missing.empty:
        st.subheader("Posts Missing Metrics")
        report_table(missing.head(30), ["platform_label", "post", "post_url"], 330)


def metric_row(df: pd.DataFrame) -> None:
    scored = df[df["has_metrics"]]
    avg_engagement = scored["total_engagements"].mean() if not scored.empty else None

    metrics = [
        ("Total Posts", fmt_number(len(df)), "Posts in the selected period", "kpi-blue"),
        (
            "Platforms",
            fmt_number(df["platform_label"].nunique() if "platform_label" in df.columns else None),
            "Social platforms collected",
            "kpi-green",
        ),
        ("Avg Engagement / Post", fmt_number(avg_engagement, 1), "Across posts with metrics", "kpi-purple"),
        (
            "Total Engagement",
            fmt_number(scored["total_engagements"].sum() if not scored.empty else None),
            "Measured engagement actions",
            "kpi-orange",
        ),
    ]
    cards = "".join(
        (
            f'<div class="kpi-card {html.escape(color_class)}">'
            f'<div class="kpi-label">{html.escape(label_text)}</div>'
            f'<div class="kpi-value">{html.escape(value_text)}</div>'
            f'<div class="kpi-card-subtitle">{html.escape(subtitle)}</div>'
            "</div>"
        )
        for label_text, value_text, subtitle, color_class in metrics
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def report_page(df: pd.DataFrame) -> None:
    report_header(df)
    metric_row(df)

    left, right = st.columns([1.4, .9])
    with left:
        section_title("Monthly Engagement Trends")
        with st.container(border=True):
            if df.empty:
                st.info("No engagement trend available for the selected filters.")
            else:
                st.altair_chart(monthly_engagement_trends_chart(df), use_container_width=True)
    with right:
        section_title("Posts by Platform")
        with st.container(border=True):
            if df.empty:
                st.info("No posts match the selected filters.")
            else:
                st.altair_chart(posts_by_platform_donut(df), use_container_width=True)

    left, right = st.columns([1, 1])
    with left:
        section_title("Average Engagement By Platform")
        with st.container(border=True):
            if df.empty:
                st.info("No engagement data available for the selected filters.")
            else:
                st.altair_chart(average_engagement_by_platform_chart(df), use_container_width=True)
    with right:
        section_title("Content Type Mix")
        with st.container(border=True):
            if df.empty:
                st.info("No content data available.")
            else:
                content_counts = (
                    df.groupby("content_type", dropna=False)
                    .agg(posts=("post_key", "count"))
                    .reset_index()
                    .sort_values("posts", ascending=False)
                    .head(8)
                )
                st.altair_chart(horizontal_bar(content_counts, "content_type", "posts", 285, "Posts"), use_container_width=True)

    section_title("Collected Posts")
    with st.container(border=True):
        if df.empty:
            st.info("No posts match the selected filters.")
        else:
            collected = df.sort_values("published_at_dt", ascending=False, na_position="last").head(30)
            report_table(collected, ["platform_label", "post", "content_type", "post_url"], 420)


def profile_followers_chart(profiles: pd.DataFrame) -> alt.Chart:
    chart_data = (
        profiles.dropna(subset=["followers_count"])
        [["platform_label", "followers_count", "followers"]]
        .rename(columns={"platform_label": "Platform", "followers_count": "Followers"})
        .sort_values("Followers", ascending=False)
    )
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Platform:N", title=None, sort="-y", axis=alt.Axis(labelAngle=-35, labelColor="#7c8494")),
            y=alt.Y("Followers:Q", title="Followers", axis=alt.Axis(labelColor="#7c8494", titleColor="#7c8494")),
            color=alt.Color("Platform:N", scale=alt.Scale(range=COLOR_RANGE), legend=None),
            tooltip=["Platform", "Followers:Q", "followers:N"],
        )
        .properties(height=310)
    )


def estimated_engagement_rate_chart(posts: pd.DataFrame, profiles: pd.DataFrame) -> alt.Chart:
    engagement = (
        posts[posts["has_metrics"]]
        .groupby("platform_label", dropna=False)
        .agg(avg_engagement=("total_engagements", "mean"), measured_posts=("post_key", "count"))
        .reset_index()
        .rename(columns={"platform_label": "Platform"})
    )
    followers = profiles[["platform_label", "followers_count"]].rename(
        columns={"platform_label": "Platform", "followers_count": "Followers"}
    )
    chart_data = engagement.merge(followers, on="Platform", how="inner").dropna(subset=["Followers"])
    chart_data = chart_data[chart_data["Followers"].gt(0)]
    chart_data["Estimated engagement rate"] = (chart_data["avg_engagement"] / chart_data["Followers"]) * 100
    chart_data = chart_data.sort_values("Estimated engagement rate", ascending=False)
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Platform:N", title=None, sort="-y", axis=alt.Axis(labelAngle=-35, labelColor="#7c8494")),
            y=alt.Y(
                "Estimated engagement rate:Q",
                title="Avg engagement / followers (%)",
                axis=alt.Axis(format=".2f", labelColor="#7c8494", titleColor="#7c8494"),
            ),
            color=alt.Color("Platform:N", scale=alt.Scale(range=COLOR_RANGE), legend=None),
            tooltip=[
                "Platform",
                alt.Tooltip("Estimated engagement rate:Q", format=".3f"),
                alt.Tooltip("avg_engagement:Q", format=".1f"),
                alt.Tooltip("Followers:Q", format=",.0f"),
                "measured_posts",
            ],
        )
        .properties(height=310)
    )


def audience_content_density_chart(profiles: pd.DataFrame) -> alt.Chart:
    chart_data = profiles[["platform_label", "followers_count", "profile_posts_count"]].rename(
        columns={
            "platform_label": "Platform",
            "followers_count": "Followers",
            "profile_posts_count": "Profile posts",
        }
    )
    chart_data = chart_data.dropna(subset=["Followers", "Profile posts"])
    chart_data = chart_data[chart_data["Profile posts"].gt(0)]
    chart_data["Followers per profile post"] = chart_data["Followers"] / chart_data["Profile posts"]
    chart_data = chart_data.sort_values("Followers per profile post", ascending=False)
    return (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("Platform:N", title=None, sort="-y", axis=alt.Axis(labelAngle=-35, labelColor="#7c8494")),
            y=alt.Y(
                "Followers per profile post:Q",
                title="Followers per profile post",
                axis=alt.Axis(labelColor="#7c8494", titleColor="#7c8494"),
            ),
            color=alt.Color("Platform:N", scale=alt.Scale(range=COLOR_RANGE), legend=None),
            tooltip=[
                "Platform",
                alt.Tooltip("Followers per profile post:Q", format=",.1f"),
                alt.Tooltip("Followers:Q", format=",.0f"),
                alt.Tooltip("Profile posts:Q", format=",.0f"),
            ],
        )
        .properties(height=310)
    )


def audience_content_density_table(profiles: pd.DataFrame) -> pd.DataFrame:
    table = profiles[["platform_label", "followers_count", "profile_posts_count"]].rename(
        columns={
            "platform_label": "Platform",
            "followers_count": "Followers",
            "profile_posts_count": "Profile posts",
        }
    )
    table = table.dropna(subset=["Followers", "Profile posts"])
    table = table[table["Profile posts"].gt(0)].copy()
    table["Followers per profile post"] = table["Followers"] / table["Profile posts"]
    return table.sort_values("Followers per profile post", ascending=False)


def profile_overview_page(posts: pd.DataFrame, profiles: pd.DataFrame) -> None:
    report_header(posts)
    st.markdown(
        '<div class="profile-note">Surface-level public profile information from the scraped social profile pages. These values describe the profiles overall, not only the posts analyzed in this report.</div>',
        unsafe_allow_html=True,
    )

    analyzed = platform_summary(posts)
    if not analyzed.empty:
        analyzed = analyzed[["Platform", "posts", "posts_with_metrics", "total_engagement"]].rename(
            columns={
                "posts": "Posts analyzed",
                "posts_with_metrics": "Analyzed posts with metrics",
                "total_engagement": "Measured engagement",
            }
        )

    if profiles.empty:
        st.info("No profile-level summary file is available yet.")
        return

    profile_cards = []
    for _, row in profiles.iterrows():
        platform = html.escape(display_value(row.get("platform_label"), "Unknown"))
        followers = html.escape(display_value(row.get("followers")))
        following = html.escape(display_value(row.get("following")))
        posts_total = html.escape(display_value(row.get("posts_or_threads")))
        profile_cards.append(
            (
                '<div class="profile-card">'
                f'<div class="profile-platform">{platform}</div>'
                f'<div class="profile-stat"><strong>Followers:</strong> {followers}</div>'
                f'<div class="profile-stat"><strong>Following:</strong> {following}</div>'
                f'<div class="profile-stat"><strong>Profile posts:</strong> {posts_total}</div>'
                "</div>"
            )
        )
    st.markdown(f'<div class="profile-grid">{"".join(profile_cards)}</div>', unsafe_allow_html=True)

    left, right = st.columns([1, 1])
    with left:
        section_title("Followers By Platform")
        with st.container(border=True):
            st.altair_chart(profile_followers_chart(profiles), use_container_width=True)
    with right:
        section_title("Estimated Engagement Rate")
        with st.container(border=True):
            st.altair_chart(estimated_engagement_rate_chart(posts, profiles), use_container_width=True)

    section_title("Audience To Content Density")
    with st.container(border=True):
        density = audience_content_density_table(profiles)
        st.dataframe(
            density,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Followers": st.column_config.NumberColumn("Followers", format="%.0f"),
                "Profile posts": st.column_config.NumberColumn("Profile posts", format="%.0f"),
                "Followers per profile post": st.column_config.NumberColumn("Followers per profile post", format="%.1f"),
            },
        )

def main() -> None:
    st.set_page_config(page_title="Goods Unite Us Social Content Report", layout="wide", initial_sidebar_state="collapsed")
    apply_theme()

    posts = load_posts()
    profiles = load_profiles()
    filtered = filtered_posts(posts)
    performance_tab, profile_tab = st.tabs(["Engagement Dashboard", "Profile Overview"])
    with performance_tab:
        report_page(filtered)
    with profile_tab:
        profile_overview_page(filtered, profiles)


if __name__ == "__main__":
    main()
