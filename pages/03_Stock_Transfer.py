import os
import requests
import streamlit as st
from datetime import date

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Stock Transfer – Marvenixx POS", layout="wide")
st.title("🔄 Stock Transfer (Cold Room → Store)")

# ========== LOAD LOCATIONS ==========
try:
    resp = requests.get(f"{API_BASE}/locations", timeout=10)
    resp.raise_for_status()
    locations = resp.json()
except Exception as e:
    st.error(f"Error loading locations: {e}")
    locations = []

if not locations:
    st.warning("No locations found. Create locations in the backend first.")
    st.stop()

loc_names = [loc["name"] for loc in locations]
name_to_id = {loc["name"]: loc["id"] for loc in locations}

c_from, c_to = st.columns(2)
with c_from:
    from_loc_name = st.selectbox("From location", loc_names, index=0)
with c_to:
    default_idx = 1 if len(loc_names) > 1 else 0
    to_loc_name = st.selectbox("To location", loc_names, index=default_idx)

if from_loc_name == to_loc_name:
    st.warning("From location and To location must be different.")

from_loc_id = name_to_id[from_loc_name]
to_loc_id = name_to_id[to_loc_name]

# ========== LOAD PRODUCTS (for SKU / name help) ==========
try:
    p_resp = requests.get(f"{API_BASE}/products", timeout=10)
    p_resp.raise_for_status()
    products = p_resp.json()
except Exception as e:
    st.error(f"Could not load product list: {e}")
    products = []

sku_to_name = {p["sku"]: p["name"] for p in products}

# ========== DYNAMIC LINES ==========
if "transfer_rows" not in st.session_state:
    st.session_state["transfer_rows"] = 1

if st.button("Add Line"):
    st.session_state["transfer_rows"] += 1

lines = []
for i in range(st.session_state["transfer_rows"]):
    with st.expander(f"Line {i+1}", expanded=True):
        sku = st.text_input("Product SKU", key=f"sku_{i}")
        if sku and sku in sku_to_name:
            st.caption(f"Product: {sku_to_name[sku]}")
        qty = st.number_input("Qty", min_value=0.0, step=0.1, key=f"qty_{i}")

        lines.append(
            {
                "product_sku": sku,
                "qty": qty,
            }
        )

# ========== POST TRANSFER ==========
if st.button("Post Transfer"):
    if from_loc_name == to_loc_name:
        st.error("From and To locations must be different.")
    else:
        payload = {
            "from_location_id": from_loc_id,
            "to_location_id": to_loc_id,
            "lines": lines,
        }
        try:
            r = requests.post(f"{API_BASE}/stock_transfer", json=payload, timeout=15)
            if r.status_code == 200:
                st.success("Stock transfer posted successfully.")
                st.json(r.json())
            else:
                st.error(f"Error from backend: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Error posting transfer: {e}")
