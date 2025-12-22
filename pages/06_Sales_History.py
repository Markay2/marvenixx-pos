import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

from auth import require_login
require_login()

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Sales History – Ateasefuor", layout="wide")
st.markdown("## 🧾 Sales History")

col_from, col_to = st.columns(2)
with col_from:
    start_date = st.date_input("From date", value=date.today().replace(day=1))
with col_to:
    end_date = st.date_input("To date", value=date.today())

if start_date > end_date:
    st.error("From date cannot be after To date.")
    st.stop()


@st.cache_data(ttl=60)
def load_sales(start_date: date, end_date: date):
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": 500,
    }
    r = requests.get(f"{API_BASE}/sales/history", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


try:
    data = load_sales(start_date, end_date)
except Exception as e:
    st.error(f"Could not load sales history: {e}")
    st.stop()

if not data:
    st.info("No sales for this period.")
else:
    df = pd.DataFrame(data)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    if "total" in df.columns:
        df["total"] = df["total"].astype(float)

    st.dataframe(df, use_container_width=True)
