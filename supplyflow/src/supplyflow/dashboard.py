from __future__ import annotations

import subprocess
import sys


def main() -> None:
    command = [sys.executable, "-m", "streamlit", "run", __file__]
    subprocess.run(command, check=False)


try:
    import pandas as pd
    import plotly.express as px
    import streamlit as st

    from supplyflow.config import LocalPaths
    from supplyflow.local_pipeline import run
except Exception:  # pragma: no cover - lets script entry fail naturally in missing envs
    pd = px = st = None


if st is not None:
    paths = LocalPaths()
    if not paths.facts_path.exists():
        run(paths)

    st.set_page_config(page_title="SupplyFlow Analytics", page_icon="📦", layout="wide")
    fact = pd.read_csv(paths.facts_path, parse_dates=["order_date"])

    st.title("📦 SupplyFlow Analytics")
    st.caption("Profitability, carrier performance, and delivery-risk monitoring from a Redshift-style mart.")

    total_revenue = fact["revenue"].sum()
    total_profit = fact["gross_profit"].sum()
    on_time_rate = fact["on_time_flag"].mean()
    avg_risk = fact["delivery_risk_score"].mean()

    left, middle_left, middle_right, right = st.columns(4)
    left.metric("Revenue", f"${total_revenue:,.0f}")
    middle_left.metric("Gross Profit", f"${total_profit:,.0f}")
    middle_right.metric("On-Time Rate", f"{on_time_rate:.1%}")
    right.metric("Avg Risk Score", f"{avg_risk:.1f}")

    trend = fact.groupby(pd.Grouper(key="order_date", freq="W"), as_index=False).agg(
        revenue=("revenue", "sum"), gross_profit=("gross_profit", "sum"), avg_risk=("delivery_risk_score", "mean")
    )
    st.plotly_chart(px.line(trend, x="order_date", y=["revenue", "gross_profit"], title="Weekly Revenue and Profit"), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        carrier = fact.groupby("carrier_id", as_index=False).agg(on_time_rate=("on_time_flag", "mean"), shipments=("shipment_id", "count"))
        st.plotly_chart(px.bar(carrier, x="carrier_id", y="on_time_rate", color="shipments", title="Carrier On-Time Rate"), use_container_width=True)
    with col2:
        risk = fact.groupby("destination_region", as_index=False).agg(avg_risk=("delivery_risk_score", "mean"))
        st.plotly_chart(px.bar(risk, x="destination_region", y="avg_risk", title="Delivery Risk by Region"), use_container_width=True)

    st.subheader("Shipment Drill-through Table")
    st.dataframe(
        fact.sort_values("delivery_risk_score", ascending=False)[
            ["shipment_id", "carrier_id", "destination_region", "service_level", "gross_profit", "late_days", "delivery_risk_score"]
        ].head(200),
        use_container_width=True,
    )
