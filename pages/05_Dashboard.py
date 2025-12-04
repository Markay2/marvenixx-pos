# 05_Dashboard.py – Detailed dashboard with custom date range

import os
from datetime import date

import requests
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Inventory & POS Dashboard – Marvenixx", layout="wide")
st.markdown("## 📊 Inventory & POS Dashboard")

# --- Date filters ---
today = date.today()
col_from, col_to = st.columns(2)
with col_from:
    start_date = st.date_input("From date", value=today.replace(day=1))
with col_to:
    end_date = st.date_input("To date", value=today)

if start_date > end_date:
    st.error("From date cannot be after To date.")
    st.stop()

# --- Load summary for that range ---
@st.cache_data(ttl=60)
def load_summary_range(start_date_str: str, end_date_str: str):
    params = {
        "start_date": start_date_str,
        "end_date": end_date_str,
    }
    r = requests.get(f"{API_BASE}/reports/sales_summary", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

try:
    summary = load_summary_range(start_date.isoformat(), end_date.isoformat())
except Exception as e:
    st.error(f"Could not load sales summary: {e}")
    st.stop()

st.caption(f"Date Range: {start_date.isoformat()} → {end_date.isoformat()}")

# --- KPIs from this range ---
k1, k2, k3 = st.columns(3)
k1.metric("Sales Today", f"₵ {summary['sales_today']:,.2f}")
k2.metric("Sales This Month", f"₵ {summary['sales_this_month']:,.2f}")
k3.metric("Sales This Year", f"₵ {summary['sales_this_year']:,.2f}")

st.markdown("---")

# --- Daily trend for the selected range ---
st.markdown("### 📈 Daily Sales Trend")

daily = summary.get("daily", [])
df = pd.DataFrame(daily)

if df.empty:
    st.info("No sales in this period.")
else:
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.set_index("date")
    df.rename(columns={"total": "Sales (₵)"}, inplace=True)
    st.line_chart(df["Sales (₵)"])

st.markdown(
    "<div style='text-align:center; font-size: 12px; color:#6b7280; margin-top: 2rem;'>"
    "Powered by <strong>Marveniss Analytics</strong> · Marvenixx POS"
    "</div>",
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div style="margin-top:40px; text-align:center; color:#6b7280; font-size:12px;">
        Powered by <strong>Marveniss Analytics</strong> · <strong>Marvenixx POS</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
