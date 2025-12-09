# app/pages/04_POS_Sales.py

import os
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="POS – Ateasefuor", layout="wide")

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.markdown("## 🧾 Point of Sale")

# --- Load products from API ---
@st.cache_data(ttl=60)
def load_products():
    """
    Use the existing /products endpoint.
    If later the API returns available_qty, we will use it;
    otherwise, POS still works without it.
    """
    r = requests.get(f"{API_BASE}/products", timeout=10)
    r.raise_for_status()
    return r.json()


try:
    products = load_products()
except Exception as e:
    st.error(f"Could not load products from API: {e}")
    st.stop()

# --- Cart state ---
if "cart" not in st.session_state:
    st.session_state["cart"] = []

cart = st.session_state["cart"]

# --- Layout: left = cart, right = products ---
left_col, right_col = st.columns([1.4, 2])

# =======================
# LEFT: CURRENT SALE / CART
# =======================
with left_col:
    st.markdown("### 🛒 Current Sale")

    cust_name = st.text_input(
        "Customer (optional)",
        value=st.session_state.get("customer_name", "")
    )

    if cart:
        st.markdown("#### Items in Cart")

        total = 0.0

        # Show each line with editable quantity and price
        for i, line in enumerate(cart):
            col_prod, col_qty, col_price, col_sub = st.columns([3, 1, 1, 1])

            with col_prod:
                st.write(line["name"])

            with col_qty:
                qty = st.number_input(
                    f"Qty_{i}",
                    min_value=0.0,
                    value=float(line.get("qty", 1.0)),
                    step=1.0,
                    key=f"qty_{i}",
                )

            with col_price:
                price = st.number_input(
                    f"Unit Price (₵)_{i}",
                    min_value=0.0,
                    value=float(line.get("unit_price", 0.0)),
                    step=0.1,
                    key=f"price_{i}",
                )

            line_total = qty * price
            total += line_total

            # Save back into cart
            line["qty"] = qty
            line["unit_price"] = price
            line["line_total"] = line_total

            with col_sub:
                st.write(f"₵ {line_total:,.2f}")

        st.markdown(f"### Total: ₵ {total:,.2f}")

        col_pay1, col_pay2, col_pay3, col_clear = st.columns(4)
        with col_pay1:
            pay_cash = st.button("💵 Cash", use_container_width=True)
        with col_pay2:
            pay_card = st.button("💳 Card", use_container_width=True)
        with col_pay3:
            pay_momo = st.button("📱 MoMo", use_container_width=True)
        with col_clear:
            clear_cart = st.button("🗑 Clear", use_container_width=True)

        if clear_cart:
            st.session_state["cart"] = []
            st.rerun()

        # Send sale to API when any payment button is pressed
        if pay_cash or pay_card or pay_momo:
            payload = {
                "customer_name": cust_name or None,
                "location_id": 1,
                "lines": [
                    {
                        "sku": line["sku"],
                        "qty": float(line["qty"]),
                        "unit_price": float(line["unit_price"]),
                    }
                    for line in cart
                ],
            }

            try:
                r = requests.post(f"{API_BASE}/sales", json=payload, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    st.success(
                        f"Sale #{data['sale_id']} recorded. Total ₵ {data['total']:,.2f}"
                    )
                    st.info(
                        f"Use the Invoice / Pro Forma page with Sale ID {data['sale_id']} "
                        "to print receipt or quotation."
                    )

                    # Optional low-stock warnings if backend sends them
                    for item in data.get("low_stock", []):
                        st.warning(
                            f"Low stock: {item['name']} (SKU {item['sku']}) – "
                            f"{item['remaining']} left."
                        )

                    st.session_state["cart"] = []
                    st.rerun()
                else:
                    st.error(f"Error from API: {r.status_code} – {r.text}")
            except Exception as e:
                st.error(f"Could not send sale to API: {e}")

    else:
        st.info("Cart is empty. Click products on the right to add items.")

# =======================
# RIGHT: PRODUCT TILES
# =======================
with right_col:
    st.markdown("### 📦 Products")

    search = st.text_input("Search by name / SKU / barcode")

    df = pd.DataFrame(products)

    if search:
        mask = (
            df["name"].str.contains(search, case=False, na=False)
            | df["sku"].astype(str).str.contains(search, case=False, na=False)
            | df["barcode"].astype(str).str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if df.empty:
        st.warning("No products match your search.")
    else:
        # Keep essential columns, including optional available_qty
        cols_keep = ["sku", "name", "unit", "selling_price", "tax_rate", "available_qty"]
        existing_cols = [c for c in cols_keep if c in df.columns]
        df = df[existing_cols].copy()

        num_cols = 4
        rows = [df.iloc[i : i + num_cols] for i in range(0, len(df), num_cols)]

        for row in rows:
            cols = st.columns(num_cols)
            for idx, (_, prod) in enumerate(row.iterrows()):
                with cols[idx]:
                    sku = prod["sku"]
                    name = prod["name"]
                    unit = prod.get("unit", "")
                    price = float(prod.get("selling_price", 0.0) or 0.0)

                    # Optional stock info if available
                    if "available_qty" in prod and prod["available_qty"] is not None:
                        avail = float(prod.get("available_qty", 0.0) or 0.0)
                        stock_line = f"Available: {avail:,.2f} {unit}".strip()
                        low_stock = avail <= 5
                        stock_color = "#dc2626" if low_stock else "#0f766e"
                    else:
                        avail = None
                        stock_line = f"Unit: {unit}".strip()
                        stock_color = "#6b7280"
                        low_stock = False

                    st.markdown(
                        f"""
                        <div style="
                            border-radius: 10px;
                            padding: 10px;
                            margin-bottom: 8px;
                            background-color: #ffffff;
                            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
                            min-height: 100px;
                        ">
                            <strong>{name}</strong><br>
                            <span style="font-size:11px;color:#6b7280;">SKU: {sku}</span><br>
                            <span style="font-size:11px;color:{stock_color};">{stock_line}</span><br>
                            <span style="font-size:12px;color:#16a34a;">₵ {price:,.2f}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button("Add", key=f"add_{sku}"):
                        cart = st.session_state.get("cart", [])

                        existing = next((c for c in cart if c["sku"] == sku), None)
                        already_qty = existing["qty"] if existing else 0.0

                        # Optional front-end oversell check if we have stock
                        if avail is not None and already_qty + 1 > avail:
                            st.warning(
                                f"Not enough stock. Available: {avail:,.2f} {unit}."
                            )
                        else:
                            if existing:
                                existing["qty"] += 1
                                existing["line_total"] = (
                                    existing["qty"] * existing["unit_price"]
                                )
                            else:
                                cart.append(
                                    {
                                        "sku": sku,
                                        "name": name,
                                        "qty": 1.0,
                                        "unit_price": price,
                                        "line_total": price,
                                    }
                                )

                            st.session_state["cart"] = cart
                            st.rerun()
