# app/pages/01_Products.py

import os
import requests
import pandas as pd
import streamlit as st

from auth import require_login
require_login()

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Products – Marvenixx POS", layout="wide")
st.title("Products")




# who is logged in (set on Home.py)
current_user = st.session_state.get("user")
current_role = current_user.get("role") if current_user else None
is_admin = current_role == "admin"

# ------------------ CREATE PRODUCT ------------------ #

st.subheader("Create new product")

with st.form("create_product"):
    c1, c2 = st.columns(2)

    # SKU is optional now – leave blank to auto-generate
    sku = c1.text_input("SKU (leave blank for auto)")

    name = c2.text_input("Name")
    barcode = c1.text_input("Barcode", value="")

    unit = c2.selectbox(
        "Unit",
        options=[
            "piece",
            "kg",
            "box",
            "carton",
            "gallon",
            "sachet",
            "bag",
            "bottle",
            "tin",
            "other",
        ],
        index=0,
    )

    tax = c1.number_input("Tax %", value=0.0, step=0.01, key="tax_create")
    selling_price = c2.number_input(
        "Selling Price (₵)",
        min_value=0.0,
        value=0.0,
        step=0.1,
        key="price_create",
    )

    submitted = st.form_submit_button("Create")
    if submitted:
        payload = {
            "sku": sku.strip() or None,
            "name": name.strip(),
            "barcode": barcode.strip() or None,
            "unit": unit,
            "tax_rate": float(tax),
            "selling_price": float(selling_price),
        }

        if not payload["name"]:
            st.error("Name is required.")
        else:
            try:
                r = requests.post(f"{API_BASE}/products", json=payload, timeout=15)
                if r.status_code == 200:
                    st.success("Product created.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Error: {r.status_code} – {r.text}")
            except Exception as e:
                st.error(f"Error creating product: {e}")

st.markdown("---")

# ------------------ LOAD ALL PRODUCTS ------------------ #

st.subheader("All products")

items = []
try:
    resp = requests.get(f"{API_BASE}/products", timeout=15)
    resp.raise_for_status()
    items = resp.json()
except Exception as e:
    st.error(f"Error fetching products: {e}")

if items:
    df_full = pd.DataFrame(items)

    # Display-friendly subset
    display_cols = [c for c in ["id", "sku", "name", "unit", "selling_price", "tax_rate"] if c in df_full.columns]
    df_display = df_full[display_cols].rename(
        columns={
            "id": "ID",
            "sku": "SKU",
            "name": "Name",
            "unit": "Unit",
            "selling_price": "Price (₵)",
            "tax_rate": "Tax %",
        }
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("No products yet.")
    df_full = pd.DataFrame([])





# ------------------ EDIT / DELETE (ADMIN ONLY) ------------------ #

if not df_full.empty:
    if is_admin:
        st.markdown("### Admin: Edit or deactivate product")

        # Sort for stable selection
        df_full = df_full.sort_values("id")

        # Build labels like "3 – Frozen Chicken (CHICK0001)"
        choices = [
            f"{row['id']} – {row['name']} ({row['sku']})"
            for _, row in df_full.iterrows()
        ]
        selected_label = st.selectbox("Choose product", choices, key="admin_product_select")

        # Extract chosen id
        selected_id = int(selected_label.split("–")[0].strip())
        selected_row = df_full[df_full["id"] == selected_id].iloc[0].to_dict()

        # ✅ Show a quick product info strip
        st.info(
            f"SKU: {selected_row.get('sku')} | "
            f"Unit: {selected_row.get('unit')} | "
            f"Price: ₵ {float(selected_row.get('selling_price') or 0):,.2f} | "
            f"Tax: {float(selected_row.get('tax_rate') or 0):.2f}% | "
            f"Barcode: {selected_row.get('barcode') or '—'}"
        )

        st.markdown(f"**Editing ID {selected_id} – {selected_row.get('name','')}**")

        # ✅ Use unique keys so values refresh when product changes
        key_name = f"name_edit_{selected_id}"
        key_barcode = f"barcode_edit_{selected_id}"
        key_unit = f"unit_edit_{selected_id}"
        key_tax = f"tax_edit_{selected_id}"
        key_price = f"price_edit_{selected_id}"

        # unit options must match create form
        unit_options = [
            "piece", "kg", "box", "carton", "gallon",
            "sachet", "bag", "bottle", "tin", "other"
        ]

        current_unit = selected_row.get("unit") or "piece"
        try:
            default_unit_idx = unit_options.index(current_unit)
        except ValueError:
            default_unit_idx = 0

        with st.form(f"edit_product_{selected_id}"):
            ec1, ec2 = st.columns(2)

            new_name = ec1.text_input("Name", value=selected_row.get("name", ""), key=key_name)
            new_barcode = ec2.text_input("Barcode", value=selected_row.get("barcode") or "", key=key_barcode)

            new_unit = ec1.selectbox(
                "Unit",
                options=unit_options,
                index=default_unit_idx,
                key=key_unit,
            )

            new_tax = ec2.number_input(
                "Tax %",
                value=float(selected_row.get("tax_rate") or 0.0),
                step=0.01,
                key=key_tax,
            )

            new_price = ec1.number_input(
                "Selling Price (₵)",
                min_value=0.0,
                value=float(selected_row.get("selling_price") or 0.0),
                step=0.1,
                key=key_price,
            )

            col_save, col_deact = st.columns(2)
            save_clicked = col_save.form_submit_button("💾 Save changes")
            deactivate_clicked = col_deact.form_submit_button("🗑 Deactivate product")

            if save_clicked:
                payload = {
                    "name": (new_name or "").strip(),
                    "barcode": (new_barcode or "").strip() or None,
                    "unit": new_unit,
                    "tax_rate": float(new_tax),
                    "selling_price": float(new_price),
                }
                try:
                    r = requests.patch(f"{API_BASE}/products/{selected_id}", json=payload, timeout=15)
                    if r.status_code == 200:
                        st.success("Product updated.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Error from API: {r.status_code} – {r.text}")
                except Exception as e:
                    st.error(f"Error calling API: {e}")

            if deactivate_clicked:
                try:
                    r = requests.delete(f"{API_BASE}/products/{selected_id}", timeout=15)
                    if r.status_code == 200:
                        st.success("Product deactivated. It will no longer appear in POS / Receive Stock.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Error from API: {r.status_code} – {r.text}")
                except Exception as e:
                    st.error(f"Error calling API: {e}")

    else:
        st.info("Log in as an admin user on the Home page to edit or deactivate products.")
