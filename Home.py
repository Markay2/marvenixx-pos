# Home.py  – Marvenixx POS main dashboard (last 7 days view)

import os
from datetime import date, timedelta

import requests
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Marvenixx POS – Dashboard", layout="wide")

st.markdown("## 📊 Marvenixx POS – Dashboard")

# --- Load sales summary (last 7 days, handled by backend default) ---
@st.cache_data(ttl=60)
def load_summary():
    r = requests.get(f"{API_BASE}/reports/sales_summary", timeout=10)
    r.raise_for_status()
    return r.json()

try:
    summary = load_summary()
except Exception as e:
    st.error(f"Could not load sales summary: {e}")
    st.stop()

# summary keys from API:
#   sales_today, sales_this_month, sales_this_year, daily (list of {date, total})

today = date.today()
seven_days_ago = today - timedelta(days=6)

with st.container():
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.caption(
            f"Showing last 7 days: {seven_days_ago.isoformat()} → {today.isoformat()}"
        )

    with col_right:
        st.markdown(
            "<div style='text-align:right; font-size: 12px; color:#6b7280;'>"
            "Powered by <strong>Marveniss Analytics</strong> · Marvenixx POS"
            "</div>",
            unsafe_allow_html=True,
        )

# --- KPI cards ---
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Sales Today", f"₵ {summary['sales_today']:,.2f}")
kpi2.metric("Sales This Month", f"₵ {summary['sales_this_month']:,.2f}")
kpi3.metric("Sales This Year", f"₵ {summary['sales_this_year']:,.2f}")

st.markdown("---")

# --- Daily sales chart (last 7 days) ---
daily = summary.get("daily", [])
df = pd.DataFrame(daily)

st.markdown("### 📈 Daily Sales – Last 7 Days")

if df.empty:
    st.info("No sales recorded in the last 7 days.")
else:
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.set_index("date")
    df.rename(columns={"total": "Sales (₵)"}, inplace=True)
    st.line_chart(df["Sales (₵)"])


st.markdown(
    """
    <style>
    /* Sidebar title */
    section[data-testid="stSidebar"] .css-1d391kg {
        font-weight: 700;
        color: #0f766e;
    }
    /* App title */
    h1, h2, h3 {
        color: #0f172a;
    }
    </style>
    """,
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
