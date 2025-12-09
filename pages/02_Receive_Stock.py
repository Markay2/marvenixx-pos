import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Receive Stock (GRN) – Marvenixx POS", layout="wide")

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.title("Receive Stock (GRN)")

# -------------- Helpers to load products & locations -------------- #
@st.cache_data(ttl=60)
def load_products():
    r = requests.get(f"{API_BASE}/products", timeout=10)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=60)
def load_locations():
    r = requests.get(f"{API_BASE}/locations", timeout=10)
    r.raise_for_status()
    return r.json()


# -------------- Load reference data -------------- #
try:
    products = load_products()
except Exception as e:
    st.error(f"Could not load product list: {e}")
    products = []

try:
    locations = load_locations()
except Exception as e:
    st.error(f"Could not load locations: {e}")
    locations = []

if not products:
    st.warning("No products found. Please create products first.")
    st.stop()

if not locations:
    st.warning("No locations found. Please create locations in the backend.")
    st.stop()

# Build mappings for easy lookup
product_by_label: dict[str, dict] = {}
for p in products:
    name = p.get("name", "Unknown")
    sku = p.get("sku", "")
    unit = p.get("unit", "")
    label = f"{name} ({sku} – {unit})" if unit else f"{name} ({sku})"
    product_by_label[label] = p

location_by_name: dict[str, dict] = {}
for loc in locations:
    loc_name = loc.get("name", f"Location {loc.get('id')}")
    location_by_name[loc_name] = loc

location_names = list(location_by_name.keys())

# -------------- Session state for dynamic lines -------------- #
if "grn_rows" not in st.session_state:
    st.session_state["grn_rows"] = 1

col_btn_add, col_btn_reset = st.columns([1, 1])
with col_btn_add:
    if st.button("➕ Add Line"):
        st.session_state["grn_rows"] += 1
with col_btn_reset:
    if st.button("🔄 Reset Lines"):
        st.session_state["grn_rows"] = 1

st.write("")

# -------------- GRN Lines Form -------------- #
lines = []
for i in range(st.session_state["grn_rows"]):
    with st.expander(f"Line {i+1}", expanded=True):
        c1, c2 = st.columns([2, 1])
        c3, c4, c5 = st.columns([1, 1, 1])

        # Product dropdown showing UNIT (Kg, Box, Gallon, Sachet, Bag, etc.)
        product_label = c1.selectbox(
            "Product (name / SKU / unit)",
            options=list(product_by_label.keys()),
            key=f"prod_{i}",
        )
        product = product_by_label[product_label]
        sku = product.get("sku")

        qty = c2.number_input(
            "Qty",
            key=f"qty_{i}",
            min_value=0.0,
            step=0.1,
            value=0.0,
        )

        unit_cost = c3.number_input(
            "Unit Cost (₵)",
            key=f"cost_{i}",
            min_value=0.0,
            step=0.01,
            value=0.0,
        )

        lot_code = c4.text_input(
            "Lot Code (optional)",
            key=f"lot_{i}",
            value="",
        )

        expiry = c5.date_input(
            "Expiry (optional)",
            key=f"exp_{i}",
            value=date.today(),
        )

        # Location by NAME, not ID
        loc_name = c1.selectbox(
            "To Location",
            options=location_names,
            key=f"loc_{i}",
        )
        loc = location_by_name[loc_name]
        loc_id = loc.get("id")

        # Collect this line
        lines.append(
            {
                "product_sku": sku,
                "qty": float(qty),
                "unit_cost": float(unit_cost),
                "lot_code": lot_code or None,
                "expiry_date": str(expiry) if expiry else None,
                "to_location_id": int(loc_id),
            }
        )

st.write("")

# -------------- Submit GRN to API -------------- #
if st.button("📥 Post GRN (Receive Stock)", type="primary"):
    # Filter out empty lines (qty = 0 or no cost)
    clean_lines = [
        ln for ln in lines
        if ln["qty"] > 0 and ln["unit_cost"] > 0 and ln["product_sku"]
    ]

    if not clean_lines:
        st.error("No valid lines to post. Please enter quantity and unit cost.")
    else:
        payload = {
            "supplier": None,  # later you can add supplier name / ID
            "lines": clean_lines,
        }
        try:
            r = requests.post(f"{API_BASE}/receipts", json=payload, timeout=15)
            r.raise_for_status()
            st.success(f"GRN posted successfully: {r.json()}")
        except Exception as e:
            st.error(f"Error sending GRN to API: {e}")
