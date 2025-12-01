import os
from datetime import date
import requests
import pandas as pd
import streamlit as st
import altair as alt

# Use the cloud API in Render, or fallback to local if not set
API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Marvenixx POS – Dashboard", layout="wide")

st.markdown("## 📊 Marvenixx POS – Dashboard")

today = date.today()
col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input("From date", value=today.replace(day=1))
with col_date2:
    end_date = st.date_input("To date", value=today)

@st.cache_data(ttl=60)
def load_sales_summary(start: date, end: date):
    params = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    r = requests.get(f"{API_BASE}/reports/sales_summary", params=params, timeout=15)
    r.raise_for_status()
    return r.json()

try:
    summary = load_sales_summary(start_date, end_date)
except Exception as e:
    st.error(f"Could not load sales summary: {e}")
    st.stop()

# Summary is expected to look like:
# {
#   "today": 123.45,
#   "this_month": 999.99,
#   "this_year": 12345.67,
#   "daily": [
#       {"date": "2025-11-01", "total": 100.0},
#       ...
#   ]
# }

today_sales = float(summary.get("today", 0.0))
month_sales = float(summary.get("this_month", 0.0))
year_sales = float(summary.get("this_year", 0.0))
daily_rows = summary.get("daily", [])

# --- KPI CARDS ---
k1, k2, k3 = st.columns(3)
with k1:
    st.metric("Sales Today", f"₵ {today_sales:,.2f}")
with k2:
    st.metric("Sales This Month", f"₵ {month_sales:,.2f}")
with k3:
    st.metric("Sales This Year", f"₵ {year_sales:,.2f}")

st.markdown("---")

# --- DAILY SALES CHART ---
if not daily_rows:
    st.info("No sales found in this date range.")
else:
    df = pd.DataFrame(daily_rows)
    # Ensure types
    df["date"] = pd.to_datetime(df["date"])
    df["total"] = df["total"].astype(float)

    st.markdown("### 📈 Daily Sales Trend")

    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x="date:T",
            y=alt.Y("total:Q", title="Sales (₵)"),
            tooltip=["date:T", "total:Q"],
        )
        .properties(height=320)
    )

    st.altair_chart(chart, use_container_width=True)

st.markdown("---")
st.caption("Powered by Marveniss Analytics · Marvenixx POS")
