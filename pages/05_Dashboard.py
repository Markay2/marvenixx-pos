# app/pages/05_Dashboard.py

import os
import requests
import pandas as pd
import streamlit as st
from datetime import date

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.title("📊 Marvenixx POS – Dashboard")

# --- Date range controls ---
today = date.today()
default_start = today.replace(day=1)

c1, c2 = st.columns(2)
start_date = c1.date_input("From date", default_start)
end_date = c2.date_input("To date", today)

summary = None

try:
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    r = requests.get(f"{API_BASE}/reports/sales_summary", params=params, timeout=15)
    r.raise_for_status()
    summary = r.json()
except Exception as e:
    st.error(f"Could not load sales summary: {e}")

if summary is not None:
    # ---- KPIs ----
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Sales Today", f"₵ {summary['sales_today']:,.2f}")
    k2.metric("Sales This Month", f"₵ {summary['sales_this_month']:,.2f}")
    k3.metric("Sales This Year", f"₵ {summary['sales_this_year']:,.2f}")

    range_total = sum(row["total"] for row in summary.get("daily", []))
    k4.metric("Total (Date Range)", f"₵ {range_total:,.2f}")

    st.markdown("---")

    # ---- Daily sales trend chart ----
    st.subheader("📈 Daily Sales Trend")

    daily = summary.get("daily", [])
    if daily:
        df = pd.DataFrame(daily)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        st.line_chart(df["total"])
    else:
        st.info("No sales in this period.")

    
    
