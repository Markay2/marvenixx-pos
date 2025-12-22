# app/pages/07_Invoice_Proforma.py

import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

from auth import require_login
require_login()

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(
    page_title="Invoice / Pro Forma – Marvenixx POS",
    layout="centered",
)

# ---------------- PRINT HELPER ----------------
def render_print_button():
    st.markdown(
        """
        <script>
        function mxpPrint(){ window.print(); }
        </script>
        """,
        unsafe_allow_html=True,
    )

    # Streamlit button + JS hook
    st.button("🖨 Print Receipt", use_container_width=True, key="print_btn")

    st.markdown(
        """
        <script>
        const btns = window.parent.document.querySelectorAll('button');
        for (const b of btns){
            if (b.innerText.trim() === "🖨 Print Receipt"){
                b.onclick = () => window.print();
            }
        }
        </script>
        """,
        unsafe_allow_html=True,
    )


# ---------------- GLOBAL CSS ----------------
st.markdown(
    """
    <style>
    @media print {
        [data-testid="stSidebar"],
        header,
        footer,
        #MainMenu,
        [data-testid="stToolbar"] {
            display: none !important;
        }
        .no-print { display:none !important; }
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
        max-width: 700px;
        margin: 0 auto;
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

# ---------------- TOP CONTROLS (NOT PRINTED) ----------------
default_sale_id = int(st.session_state.get("last_sale_id") or 1)
default_doc = st.session_state.get("last_doc_type") or "Receipt"

st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown("## 🧾 Invoice / Pro Forma")

c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    doc_type = st.selectbox(
        "Document type",
        ["Receipt", "Proforma"],
        index=0 if default_doc == "Receipt" else 1,
        key="doc_type",
    )
with c2:
    sale_id = st.number_input(
        "Sale ID",
        min_value=1,
        step=1,
        value=default_sale_id,
        key="sale_id_input",
    )
with c3:
    auto_print = st.checkbox("Auto-print after Load", value=False, key="auto_print_checkbox")

load_clicked = st.button("Load document", use_container_width=True, key="load_doc_btn")
st.caption("Tip: Click **Load document** then click **Print Receipt**.")
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- LOAD SALE ----------------
sale = None
lines = []

if load_clicked:
    try:
        r = requests.get(f"{API_BASE}/sales/{int(sale_id)}", timeout=15)
        r.raise_for_status()
        data = r.json()
        sale = data.get("sale")
        lines = data.get("lines", [])
        st.session_state["last_sale_id"] = int(sale_id)
        st.session_state["last_doc_type"] = doc_type
    except Exception as e:
        st.error(f"Error loading sale: {e}")
        sale = None
        lines = []

# ---------------- COMPUTED FIELDS ----------------
user = st.session_state.get("user") or {}
served_by = (user.get("full_name") or user.get("username") or "").strip()

# Payment method stored from POS (we’ll set this in POS after payment)
payment_method = st.session_state.get("last_payment_method", "Cash / MoMo").strip()

# ---------------- RENDER RECEIPT ----------------
if sale is not None:
    st.markdown('<div class="invoice-box">', unsafe_allow_html=True)

    # HEADER
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

    # META
    raw_date = sale.get("created_at", "")
    if raw_date:
        try:
            dt = datetime.fromisoformat(raw_date)
            sale_date = dt.strftime("%Y-%m-%d")
        except Exception:
            sale_date = raw_date[:10]
    else:
        sale_date = ""

    printed_time = datetime.now().strftime("%H:%M")
    customer = sale.get("customer_name") or "Walk-in Customer"

    m1, m2 = st.columns(2)
    with m1:
        st.write(f"**{doc_type.upper()}**")
        st.write(f"**Customer:** {customer}")
        if served_by:
            st.write(f"**Served by:** {served_by}")
    with m2:
        st.write(f"**Date:** {sale_date} {printed_time}")
        st.write(f"**Sale ID:** {sale.get('id', '')}")

    st.write("")

    # LINES TABLE
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

        for col in ["Qty", "Unit Price (₵)", "Line Total (₵)"]:
            if col in df.columns:
                df[col] = df[col].astype(float).map(lambda x: f"{x:,.2f}")

        st.table(df)
    else:
        st.info("No line items for this sale.")

    # TOTAL
    total = sale.get("total") or sale.get("total_amount") or 0
    try:
        total_val = float(total)
    except Exception:
        total_val = 0.0

    st.write("")
    st.write(f"### Total: ₵ {total_val:,.2f}")

    # PAYMENT SUMMARY
    st.write("")
    st.write("#### Payment summary")
    st.write(f"- Method: **{payment_method}**")
    st.write(f"- Amount paid: ₵ {total_val:,.2f}")
    st.write(f"- Balance: ₵ 0.00")

    st.write("---")
    st.caption("Thank you for your business.")

    st.markdown("</div>", unsafe_allow_html=True)

    # PRINT CONTROLS (NOT PRINTED)
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    render_print_button()
    st.markdown("</div>", unsafe_allow_html=True)

    # OPTIONAL AUTO PRINT
    if auto_print:
        st.markdown(
            """
            <script>
            window.setTimeout(() => { window.print(); }, 600);
            </script>
            """,
            unsafe_allow_html=True,
        )

else:
    st.info("Load a Sale ID to view and print a receipt / proforma.")
