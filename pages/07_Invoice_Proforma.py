import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Invoice / Pro Forma – Ateasefuor", layout="wide")

st.markdown("## 🧾 Invoice / Pro Forma")

# Choose whether you're printing a receipt or pro forma
doc_type = st.radio(
    "Document type",
    ["Receipt", "Pro Forma Invoice"],
    horizontal=True,
)

sale_id = st.number_input("Sale ID", min_value=1, step=1, value=1)

if st.button("Load Sale"):
    try:
        r = requests.get(f"{API_BASE}/sales/{int(sale_id)}", timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Error loading sale: {e}")
    else:
        # Backend can return {"sale": {...}, "lines": [...]}
        # or a flat dict with .lines
        if isinstance(data, dict) and "sale" in data:
            sale = data["sale"]
            lines = data.get("lines", [])
        else:
            sale = data
            lines = data.get("lines", [])

        # --- COMPANY HEADER (edit text to match real details) ---
        st.markdown("---")

        # Top header block – what will show on the printed receipt/proforma
        left, right = st.columns([2, 1.2])

        with left:
            st.markdown(
                f"""
                <div style="line-height: 1.2;">
                    <h2 style="margin-bottom:0;">Ateasefuor Limited Company</h2>
                    <p style="margin:0;font-size:13px;">
                        Cold Foods & Grocery<br>
                        (Edit address, phone, email here)
                    </p>
                    <p style="margin:0;font-size:13px;color:#64748b;">
                        Powered by <strong>Marvenixx POS</strong>
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            # Document title based on selection
            title = "RECEIPT" if doc_type == "Receipt" else "PRO FORMA INVOICE"
            st.markdown(
                f"""
                <div style="
                    border:1px solid #e5e7eb;
                    border-radius:8px;
                    padding:8px 12px;
                    text-align:right;
                    font-size:13px;
                ">
                    <div style="font-size:18px;font-weight:700;">{title}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # --- BASIC SALE INFO ---
        created_at_raw = sale.get("created_at")
        created_at_str = ""
        if created_at_raw:
            try:
                dt_obj = (
                    datetime.fromisoformat(created_at_raw.replace("Z", ""))
                    if isinstance(created_at_raw, str)
                    else created_at_raw
                )
                created_at_str = dt_obj.strftime("%d %b %Y, %H:%M")
            except Exception:
                created_at_str = str(created_at_raw)

        customer = sale.get("customer_name") or "Walk-in customer"
        location_id = sale.get("location_id", "")
        total_val = float(sale.get("total", sale.get("total_amount", 0.0)) or 0.0)

        info_left, info_right = st.columns(2)

        with info_left:
            st.markdown(
                f"""
                **Sale ID:** {sale.get('id')}  
                **Customer:** {customer}  
                **Date & Time:** {created_at_str}
                """.strip()
            )

        with info_right:
            st.markdown(
                f"""
                **Location ID:** {location_id}  
                **Grand Total:** ₵ {total_val:,.2f}
                """.strip()
            )

        st.markdown("---")

        # --- LINE ITEMS TABLE ---
        if lines:
            df = pd.DataFrame(lines)

            # Try to keep only useful columns if they exist
            preferred_order = [
                "product_sku",
                "product_name",
                "qty",
                "unit_price",
                "line_total",
            ]
            cols = [c for c in preferred_order if c in df.columns]
            if cols:
                df = df[cols]

            # Rename for nicer display
            rename_map = {
                "product_sku": "SKU",
                "product_name": "Product",
                "qty": "Qty",
                "unit_price": "Unit Price (₵)",
                "line_total": "Line Total (₵)",
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

            st.table(df)

            # Compute subtotal if needed
            if "line_total" in df.columns:
                try:
                    subtotal = float(df["Line Total (₵)"].astype(float).sum())
                except Exception:
                    subtotal = total_val
            else:
                subtotal = total_val

            st.markdown(
                f"""
                <div style="text-align:right;font-size:14px;margin-top:10px;">
                    <strong>Grand Total: ₵ {total_val:,.2f}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No line items found for this sale.")

        st.markdown("---")

        # Footer note different for Receipt vs Pro Forma
        if doc_type == "Pro Forma Invoice":
            st.caption(
                "This is a **Pro Forma Invoice** and not a final receipt. "
                "Goods/services will be supplied upon confirmation of payment."
            )
        else:
            st.caption(
                "Thank you for your purchase! Keep this receipt as proof of payment."
            )

        st.caption(
            "To print, use your browser's **Print** function (Ctrl+P / Cmd+P) "
            "and choose PDF or a physical printer."
        )
