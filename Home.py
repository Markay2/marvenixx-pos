# Home.py

import os
import requests
import streamlit as st
from datetime import date

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Marvenixx POS – Home", layout="wide")

st.title("Marvenixx POS – Dashboard")

# ---------- SIMPLE USER STORE ----------
# You can change these users/passwords later.
USERS = {
    "Gerty": {"password": "Gerty123", "full_name": "Gertrude", "role": "admin"},
    "Admin": {"password": "Admin123", "full_name": "David", "role": "admin"},
    "Cecy": {"password": "cashier1", "full_name": "Cecilia", "role": "cashier"},
}

# Session store for the logged-in user
if "user" not in st.session_state:
    st.session_state["user"] = None

# ---------- LAYOUT: KPIs LEFT, LOGIN RIGHT ----------
left_col, right_col = st.columns([2, 1])

# --- LEFT: Quick KPIs + WhatsApp summary ---
with left_col:
    st.subheader("Today’s KPIs")

    try:
        r = requests.get(f"{API_BASE}/reports/sales_summary", timeout=10)
        r.raise_for_status()
        summary = r.json()

        k1, k2, k3 = st.columns(3)
        k1.metric("Sales Today", f"₵ {summary['sales_today']:,.2f}")
        k2.metric("Sales This Month", f"₵ {summary['sales_this_month']:,.2f}")
        k3.metric("Sales This Year", f"₵ {summary['sales_this_year']:,.2f}")

        # WhatsApp text
        today_str = date.today().isoformat()
        wa_text = (
            f"*Ateasefuor Limited – Daily Sales Summary* ({today_str})\n"
            f"Sales today: ₵ {summary['sales_today']:,.2f}\n"
            f"Sales this month: ₵ {summary['sales_this_month']:,.2f}\n"
            f"Sales this year: ₵ {summary['sales_this_year']:,.2f}\n"
        )

        st.markdown("### 📱 WhatsApp daily summary")
        st.text_area(
            "Copy & paste this into WhatsApp for the owner:",
            value=wa_text,
            height=150,
        )
    except Exception as e:
        st.error(f"Could not load KPIs: {e}")

    st.markdown("---")
    st.caption("Go to *POS Sales* to record transactions and *Invoice Proforma* to print receipts.")

# --- RIGHT: Login / Logout ---
with right_col:
    st.subheader("Staff login")

    if st.session_state["user"] is not None:
        user = st.session_state["user"]
        name = user.get("full_name") or user.get("username")
        role = user.get("role", "user")
        st.success(f"Logged in as **{name}** ({role})")

        if st.button("Log out"):
            st.session_state["user"] = None
            st.rerun()            # 👈 IMPORTANT: use st.rerun
    else:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            record = USERS.get(username)
            if record and password == record["password"]:
                st.session_state["user"] = {
                    "username": username,
                    "full_name": record.get("full_name"),
                    "role": record.get("role", "user"),
                }
                st.success("Login successful. You can now go to POS Sales and Invoice Proforma.")
                st.rerun()        # 👈 same here
            else:
                st.error("Invalid username or password.")
