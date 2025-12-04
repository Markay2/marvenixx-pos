import streamlit as st
import requests
import os
from datetime import date

st.title("Receive Stock (GRN)")

API_BASE = os.getenv("API_BASE", "http://api:8000")

# ---------- Load products & locations ----------

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

try:
    PRODUCTS = load_products()
except Exception as e:
    st.error(f"Could not load product list: {e}")
    PRODUCTS = []

try:
    LOCATIONS = load_locations()
except Exception as e:
    st.error(f"Could not load locations: {e}")
    LOCATIONS = []


# ---------- Dynamic lines ----------

if "rows" not in st.session_state:
    st.session_state["rows"] = 1

if st.button("Add Line"):
    st.session_state["rows"] += 1

lines = []

for i in range(st.session_state["rows"]):
    with st.expander(f"Line {i+1}", expanded=True):

        # PRODUCT: search by SKU or name (type in the box)
        if PRODUCTS:
            prod_label_to_sku = {}
            for p in PRODUCTS:
                label = f"{p['sku']} – {p['name']}"
                prod_label_to_sku[label] = p["sku"]

            prod_labels = list(prod_label_to_sku.keys())

            selected_prod_label = st.selectbox(
                "Product (type SKU or name)",
                options=prod_labels,
                key=f"prod_{i}",
            )
            sku = prod_label_to_sku[selected_prod_label]
        else:
            sku = st.text_input("Product SKU", key=f"sku{i}")

        qty = st.number_input("Qty", key=f"qty{i}", min_value=0.0, step=0.1)
        cost = st.number_input("Unit Cost", key=f"cost{i}", min_value=0.0, step=0.01)
        lot = st.text_input("Lot Code (optional)", key=f"lot{i}", value="")
        exp = st.date_input("Expiry (optional)", key=f"exp{i}", value=date.today())

        # LOCATION: choose by name instead of ID
        if LOCATIONS:
            loc_name_to_id = {loc["name"]: loc["id"] for loc in LOCATIONS}
            loc_names = list(loc_name_to_id.keys())

            selected_loc_name = st.selectbox(
                "To Location",
                options=loc_names,
                key=f"loc_{i}",
            )
            loc_id = loc_name_to_id[selected_loc_name]
        else:
            # Fallback if locations API fails
            loc_id = st.number_input(
                "To Location ID",
                key=f"loc{i}",
                min_value=1,
                value=1,
            )

        lines.append(
            {
                "product_sku": sku,
                "qty": qty,
                "unit_cost": cost,
                "lot_code": lot or None,
                "expiry_date": str(exp),
                "to_location_id": int(loc_id),
            }
        )

# ---------- Post GRN ----------

if st.button("Post GRN"):
    payload = {"supplier": None, "lines": lines}
    try:
        r = requests.post(f"{API_BASE}/receipts", json=payload, timeout=10)
        if r.status_code == 200:
            st.success("GRN posted successfully.")
            st.json(r.json())
        else:
            st.error(f"Error from API: {r.status_code} – {r.text}")
    except Exception as e:
        st.error(f"Error sending receipt: {e}")
