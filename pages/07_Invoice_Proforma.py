# app/pages/07_Invoice_Proforma.py

import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(
    page_title="Invoice / Pro Forma – Marvenixx POS",
    layout="centered",
)

# ==================== GLOBAL CSS ==================== #
st.markdown(
    """
    <style>
    @media print {
        /* Hide sidebar + Streamlit chrome when printing */
        [data-testid="stSidebar"],
        header,
        footer,
        #MainMenu,
        [data-testid="stToolbar"] {
            display: none !important;
        }
        .block-container {
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        @page {
            size: A4 portrait;
            margin: 10mm;
        }
    }

    .invoice-box {
        background: #ffffff;
        padding: 20px 30px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        font-size: 13px;
    }

    .company-name {
        font-size: 18px;
        font-weight: 900;
        text-align: center;
        margin-bottom: 2px;
    }

    .company-contact {
        font-size: 11px;
        text-align: center;
        line-height: 1.3;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================== CONTROLS IN SIDEBAR (NOT PRINTED) ==================== #
with st.sidebar:
    st.markdown("## 🧾 Invoice / Pro Forma")

    doc_type = st.selectbox("Document type", ["Receipt", "Proforma"])
    sale_id = st.number_input("Sale ID", min_value=1, step=1, value=1)

    # Try to auto-fill from logged in user later
    default_served_by = ""
    user = st.session_state.get("user")
    if user:
        default_served_by = user.get("full_name") or user.get("username") or ""

    served_by = st.text_input("Served by", value=default_served_by)

    payment_method = st.selectbox(
        "Payment method",
        ["Cash", "Mobile Money", "Card", "Other"],
        index=0,
    )

    load_clicked = st.button("Load document")

# ==================== LOAD SALE FROM API ==================== #
sale = None
lines = []

if load_clicked:
    try:
        r = requests.get(f"{API_BASE}/sales/{int(sale_id)}", timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Error loading sale: {e}")
    else:
        if isinstance(data, dict) and "sale" in data:
            sale = data["sale"]
            lines = data.get("lines", [])
        else:
            sale = data
            lines = data.get("lines", [])

# ==================== INVOICE CONTENT (THIS IS WHAT PRINTS) ==================== #
if sale is not None:
    st.markdown('<div class="invoice-box">', unsafe_allow_html=True)

    # ---- HEADER: LOGO + TEXT ----
    col_logo, col_text, col_empty = st.columns([1, 3, 1])

    with col_logo:
        try:
            st.image("logo.png", width=90)
        except Exception:
            pass

    with col_text:
        st.markdown(
            '<div class="company-name">ATEASEFUOR LIMITED COMPANY</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="company-contact">
                Opp Redco Flat, Madina New Market, Accra, Ghana<br/>
                Mobile: 0201497272 / 0530461935 • www.ateasefuor.com
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("---")

    # ---- META INFO ----
    raw_date = sale.get("created_at", "")
    if raw_date:
        try:
            dt = datetime.fromisoformat(raw_date)
            sale_date = dt.strftime("%Y-%m-%d")
        except Exception:
            sale_date = raw_date[:10]
    else:
        sale_date = ""

    # printed time (current time)
    printed_time = datetime.now().strftime("%H:%M")

    customer = sale.get("customer_name") or "Walk-in Customer"

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**{doc_type.upper()}**")
        st.write(f"**Customer:** {customer}")
        if served_by.strip():
            st.write(f"**Served by:** {served_by.strip()}")
    with c2:
        # Date + time together
        st.write(f"**Date:** {sale_date} {printed_time}")
        st.write(f"**Sale ID:** {sale.get('id', '')}")

    st.write("")

    # ---- LINES TABLE ----
    if lines:
        df = pd.DataFrame(lines)

        if "product_name" not in df.columns and "name" in df.columns:
            df["product_name"] = df["name"]

        rename_map = {
            "product_name": "Item",
            "qty": "Qty",
            "unit_price": "Unit Price (₵)",
            "line_total": "Line Total (₵)",
        }
        df = df.rename(columns=rename_map)

        wanted = ["Item", "Qty", "Unit Price (₵)", "Line Total (₵)"]
        cols = [c for c in wanted if c in df.columns]
        df = df[cols]

        # 2 decimal places
        for col in ["Qty", "Unit Price (₵)", "Line Total (₵)"]:
            if col in df.columns:
                df[col] = df[col].astype(float).map(lambda x: f"{x:,.2f}")

        st.table(df)
    else:
        st.info("No line items for this sale.")

    # ---- TOTAL ----
    total = sale.get("total") or sale.get("total_amount") or 0
    try:
        total_val = float(total)
    except Exception:
        total_val = 0.0

    st.write("")
    st.write(f"### Total: ₵ {total_val:,.2f}")

    # ---- PAYMENT SUMMARY ----
    st.write("")
    st.write("#### Payment summary")
    st.write(f"- Method: **{payment_method}**")
    st.write(f"- Amount paid: ₵ {total_val:,.2f}")
    st.write(f"- Balance: ₵ 0.00")

    st.write("---")
    st.caption("Thank you for your business.")

    st.markdown("</div>", unsafe_allow_html=True)

else:
    if load_clicked:
        st.warning("No sale data returned. Please check the Sale ID.")
    else:
        st.info("Use the controls in the left sidebar to load a receipt or proforma.")