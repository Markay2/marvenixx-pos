import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Dashboard – Ateasefuor", layout="wide")

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.markdown("## 📊 Inventory & POS Dashboard")

# date range filters for the graph
col_from, col_to = st.columns(2)
with col_from:
    start_date = st.date_input("From date", value=date.today().replace(day=1))
with col_to:
    end_date = st.date_input("To date", value=date.today())

if start_date > end_date:
    st.error("From date cannot be after To date.")
    st.stop()


@st.cache_data(ttl=60)
def load_summary(start_date: date, end_date: date):
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    r = requests.get(f"{API_BASE}/reports/sales_summary", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


try:
    summary = load_summary(start_date, end_date)
except Exception as e:
    st.error(f"Could not load sales summary: {e} (URL: {API_BASE}/reports/sales_summary)")
    st.stop()

# top KPIs
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Sales Today", f"₵ {summary['sales_today']:,.2f}")
with k2:
    st.metric("Sales This Month", f"₵ {summary['sales_this_month']:,.2f}")
with k3:
    st.metric("Sales This Year", f"₵ {summary['sales_this_year']:,.2f}")
with k4:
    st.metric("Date Range", f"{start_date} → {end_date}")

# line chart for selected period
by_day = summary.get("by_day", [])
if not by_day:
    st.info("No sales in this period.")
else:
    df = pd.DataFrame(by_day)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    st.markdown("### Sales over time")
    st.line_chart(df.set_index("date")["total"])
