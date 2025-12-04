import streamlit as st
import requests
import os
import pandas as pd

st.title("Products")

API_BASE = os.getenv("API_BASE", "http://api:8000")

with st.form("create_product"):
    c1, c2 = st.columns(2)

    sku = c1.text_input("SKU")
    name = c2.text_input("Name")

    barcode = c1.text_input("Barcode", value="")

    # 🔽 UNIT DROPDOWN
    unit_choice = c2.selectbox(
        "Unit",
        ["unit", "kg", "box", "gallon", "piece", "pack", "crate", "carton", "other"],
    )
    if unit_choice == "other":
        unit_custom = c2.text_input("Custom unit (e.g. tray, bundle)")
        unit_value = unit_custom.strip() or "unit"
    else:
        unit_value = unit_choice

    tax = c1.number_input("Tax %", value=0.0, step=0.01)

    selling_price = st.number_input(
        "Selling Price (₵)",
        min_value=0.0,
        value=0.0,
        step=0.1,
    )

    submitted = st.form_submit_button("Create")

    if submitted:
        payload = {
            "sku": sku,
            "name": name,
            "barcode": barcode or None,
            "unit": unit_value,          # 👈 use dropdown/custom value
            "tax_rate": tax,
            "selling_price": selling_price,
        }
        try:
            r = requests.post(f"{API_BASE}/products", json=payload, timeout=10)
            if r.status_code == 200:
                st.success("Product created successfully.")
            else:
                st.error(f"Error from API: {r.status_code} – {r.text}")
        except Exception as e:
            st.error(f"Error creating product: {e}")

st.subheader("All Products")
try:
    resp = requests.get(f"{API_BASE}/products", timeout=10)
    resp.raise_for_status()
    items = resp.json()

    if isinstance(items, list) and items:
        st.dataframe(pd.DataFrame(items))
    else:
        st.info("No products yet.")
except Exception as e:
    st.error(f"Error fetching products: {e}")
