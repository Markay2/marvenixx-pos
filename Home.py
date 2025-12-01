import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Ateasefuor – Home", layout="wide")

st.markdown("## 🧊 Ateasefuor Limited")
st.markdown("### Inventory & POS Dashboard")

st.write(f"**Date:** {date.today():%d %b %Y}")


@st.cache_data(ttl=60)
def load_summary():
    # No query params here – backend will default to last 7 days
    r = requests.get(f"{API_BASE}/reports/sales_summary", timeout=10)
    r.raise_for_status()
    return r.json()


try:
    summary = load_summary()
except Exception as e:
    st.error(f"Could not load sales summary: {e}")
    st.stop()

# ---- KPI CARDS (match keys from API) ----
kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    st.metric("Sales Today", f"₵ {summary['sales_today']:,.2f}")
with kpi2:
    st.metric("Sales This Month", f"₵ {summary['sales_this_month']:,.2f}")
with kpi3:
    st.metric("Sales This Year", f"₵ {summary['sales_this_year']:,.2f}")

st.markdown("---")

# ---- SALES GRAPH FOR LAST 7 DAYS ----
daily = summary.get("daily", [])
if not daily:
    st.info("No sales in the last 7 days.")
else:
    df = pd.DataFrame(daily)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    st.markdown("### Sales – Last 7 Days")
    st.line_chart(df.set_index("date")["total"])
