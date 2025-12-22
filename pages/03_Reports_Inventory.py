import streamlit as st
import requests
import os
import pandas as pd

from auth import require_login
require_login()

st.title("Reports — Inventory On Hand")

API_BASE = os.getenv("API_BASE", "http://api:8000")

try:
    r = requests.get(f"{API_BASE}/reports/inventory")
    data = r.json().get("items", [])
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df)

        # 👉 CSV download button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download inventory as CSV",
            csv,
            "inventory_on_hand.csv",
            "text/csv",
        )
    else:
        st.info("No inventory yet. Receive stock first.")
except Exception as e:
    st.error(f"Error fetching inventory report: {e}")
