import os
import requests
import pandas as pd
import streamlit as st

st.title("Products")

API_BASE = os.getenv("API_BASE", "http://api:8000")

# ---------- Create product ----------
with st.form("create_product"):
    c1, c2 = st.columns(2)
    sku = c1.text_input("SKU")
    name = c2.text_input("Name")
    barcode = c1.text_input("Barcode", value="")
    unit_choice = c2.selectbox(
    "Unit",
    ["Pieces", "Kg", "Box", "Gallon", "Carton", "Packet", "Bottle", "Tray", "Other"],
    index=0,
    )

    custom_unit = ""
    if unit_choice == "Other":
      custom_unit = c2.text_input("Custom unit (optional)", value="")

    unit = custom_unit.strip() if unit_choice == "Other" and custom_unit.strip() else unit_choice
    tax = c1.number_input("Tax %", value=0.0, step=0.01)
    selling_price = st.number_input(
        "Selling Price (₵)",
        min_value=0.0,
        value=0.0,
        step=0.10,
    )
    submitted = st.form_submit_button("Create")
    if submitted:
        payload = {
            "sku": sku,
            "name": name,
            "barcode": barcode or None,
            "unit": unit,
            "tax_rate": tax,
            "selling_price": selling_price,
        }
        try:
            r = requests.post(f"{API_BASE}/products", json=payload, timeout=10)
            if r.status_code == 200:
                st.success("Product created.")
            else:
                st.error(f"Error: {r.text}")
        except Exception as e:
            st.error(f"Error creating product: {e}")

st.subheader("All Products")
items = []
try:
    r = requests.get(f"{API_BASE}/products", timeout=10)
    r.raise_for_status()
    items = r.json()
except Exception as e:
    st.error(f"Error fetching products: {e}")

if isinstance(items, list) and items:
    df = pd.DataFrame(items)
    st.dataframe(df, use_container_width=True)

    # ------- Delete product section -------
    st.markdown("### Delete a product")

    # Build options "ID – Name (SKU)"
    options_map = {
        f"{row['id']} – {row.get('name','')} ({row.get('sku','')})": row["id"]
        for row in items
    }
    option_label = st.selectbox(
        "Select product to delete",
        list(options_map.keys()),
        index=0,
        key="delete_product_select",
    )
    if st.button("Delete selected product"):
        product_id = options_map[option_label]
        try:
            resp = requests.delete(
                f"{API_BASE}/products/{product_id}",
                timeout=10,
            )
            if resp.status_code == 200:
                st.success("Product deleted. Refresh page to see changes.")
            else:
                st.error(f"Error deleting: {resp.text}")
        except Exception as e:
            st.error(f"Error deleting product: {e}")

else:
    st.info("No products yet.")
