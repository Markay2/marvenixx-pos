# app/pages/03_Stock_Transfer.py

import os
import requests
import streamlit as st
from datetime import date

from auth import require_login
require_login()

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

st.markdown("---")

# ========== LOAD PRODUCTS (for dropdown + unit help) ==========
try:
    p_resp = requests.get(f"{API_BASE}/products", timeout=10)
    p_resp.raise_for_status()
    products = p_resp.json()
except Exception as e:
    st.error(f"Could not load product list: {e}")
    products = []

if not products:
    st.warning("No products available. Create products first on Products page.")
    st.stop()

# Build label → sku / unit map
product_labels = []
label_to_sku = {}
sku_to_unit = {}

for p in products:
    sku = p.get("sku", "")
    name = p.get("name", "")
    unit = p.get("unit", "")
    label = f"{name} [{sku}] ({unit})" if unit else f"{name} [{sku}]"
    product_labels.append(label)
    label_to_sku[label] = sku
    sku_to_unit[sku] = unit

# ========== DYNAMIC LINES ==========
st.subheader("Lines")

if "transfer_rows" not in st.session_state:
    st.session_state["transfer_rows"] = 1

c_add, c_reset = st.columns(2)
with c_add:
    if st.button("➕ Add Line"):
        st.session_state["transfer_rows"] += 1
with c_reset:
    if st.button("🧹 Clear Lines"):
        st.session_state["transfer_rows"] = 1

lines = []
for i in range(st.session_state["transfer_rows"]):
    with st.expander(f"Line {i+1}", expanded=True):
        prod_label = st.selectbox(
            "Product",
            product_labels,
            key=f"prod_{i}",
        )
        sku = label_to_sku[prod_label]
        unit = sku_to_unit.get(sku, "")

        st.caption(f"SKU: **{sku}** – Unit: **{unit}**")

        qty = st.number_input(
            "Qty",
            min_value=0.0,
            step=0.1,
            key=f"qty_{i}",
        )

        lines.append(
            {
                "product_sku": sku,
                "qty": qty,
            }
        )

st.markdown("---")

# ========== POST TRANSFER ==========
if st.button("Post Transfer"):
    if from_loc_name == to_loc_name:
        st.error("From and To locations must be different.")
    elif not any(line["qty"] > 0 for line in lines):
        st.error("At least one line must have a quantity > 0.")
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
