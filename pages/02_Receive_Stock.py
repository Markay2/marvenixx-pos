import streamlit as st
import requests
import os
from datetime import date

st.title("Receive Stock (GRN)")

API_BASE = os.getenv("API_BASE", "http://api:8000")

if "rows" not in st.session_state:
    st.session_state["rows"] = 1

if st.button("Add Line"):
    st.session_state["rows"] += 1

lines = []
for i in range(st.session_state["rows"]):
    with st.expander(f"Line {i+1}", expanded=True):
        sku = st.text_input("Product SKU", key=f"sku{i}")
        qty = st.number_input("Qty", key=f"qty{i}", min_value=0.0, step=0.1)
        cost = st.number_input("Unit Cost", key=f"cost{i}", min_value=0.0, step=0.01)
        lot = st.text_input("Lot Code (optional)", key=f"lot{i}", value="")
        exp = st.date_input("Expiry (optional)", key=f"exp{i}", value=date.today())
        loc = st.number_input("To Location ID", key=f"loc{i}", min_value=1, value=1)
        lines.append(
            {
                "product_sku": sku,
                "qty": qty,
                "unit_cost": cost,
                "lot_code": lot or None,
                "expiry_date": str(exp),
                "to_location_id": int(loc),
            }
        )

if st.button("Post GRN"):
    payload = {"supplier": None, "lines": lines}
    try:
        r = requests.post(f"{API_BASE}/receipts", json=payload)
        if r.status_code == 200:
            st.success(r.json())
        else:
            st.error(r.text)
    except Exception as e:
        st.error(f"Error sending receipt: {e}")
