import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Invoice / Pro Forma – Marvenixx POS", layout="wide")

st.markdown("## 🧾 Invoice / Pro Forma")

# Choose document type: affects heading + note
doc_type = st.radio(
    "Document type",
    ["Receipt", "Pro Forma"],
    horizontal=True,
)

sale_id = st.number_input("Sale ID", min_value=1, step=1, value=1)

if st.button("Load Document", type="primary"):
    try:
        r = requests.get(f"{API_BASE}/sales/{int(sale_id)}", timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Error loading sale: {e}")
    else:
        # Backend may return {"sale": {...}, "lines": [...]}
        # or a flat object that already has "lines".
        if isinstance(data, dict) and "sale" in data:
            sale = data["sale"]
            lines = data.get("lines", [])
        else:
            sale = data
            lines = data.get("lines", [])

        # Extract fields safely
        sale_id_val = sale.get("id")
        customer_name = sale.get("customer_name") or "Walk-in"

        # created_at may be ISO string; format nicely if present
        created_raw = sale.get("created_at")
        if created_raw:
            try:
                created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                created_str = created_dt.strftime("%d %b %Y, %H:%M")
            except Exception:
                created_str = str(created_raw)
        else:
            created_str = "-"

        # Total may be under "total" or "total_amount"
        total_val = sale.get("total")
        if total_val is None:
            total_val = sale.get("total_amount", 0.0)

        # ==== HEADER ====
        title_text = "SALES RECEIPT" if doc_type == "Receipt" else "PRO FORMA INVOICE"

        st.markdown(
            f"""
            <div style="padding: 10px 0 20px 0;">
                <div style="font-size:26px; font-weight:700;">Marvenixx POS</div>
                <div style="color:#6b7280;">Powered by Marveniss Analytics</div>
            </div>
            <div style="margin-top:10px; margin-bottom:20px;">
                <span style="font-size:20px; font-weight:600;">{title_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_info1, col_info2 = st.columns(2)

        with col_info1:
            st.write(f"**Sale ID:** {sale_id_val}")
            st.write(f"**Customer:** {customer_name}")
        with col_info2:
            st.write(f"**Date:** {created_str}")
            st.write(f"**Total:** ₵ {float(total_val or 0):,.2f}")

        st.markdown("---")

        # ==== LINE ITEMS TABLE ====
        if lines:
            df = pd.DataFrame(lines)

            # Reorder/rename columns if we recognise them
            preferred_cols = []
            for c in ["product_name", "name", "sku", "qty", "unit_price", "line_total"]:
                if c in df.columns:
                    preferred_cols.append(c)
            if preferred_cols:
                df = df[preferred_cols]

            # Nice column labels
            rename_map = {
                "product_name": "Product",
                "name": "Product",
                "sku": "SKU",
                "qty": "Qty",
                "unit_price": "Unit Price (₵)",
                "line_total": "Line Total (₵)",
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

            st.table(df)
        else:
            st.info("No line items found for this sale.")

        st.markdown("---")

        # ==== FOOTER NOTE ====
        if doc_type == "Pro Forma":
            st.markdown(
                """
                <div style="font-size:11px; color:#9ca3af;">
                    This is a <strong>Pro Forma Invoice</strong> (quotation only).
                    Goods and services are not yet supplied and this is not a tax receipt.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="font-size:11px; color:#9ca3af;">
                    Thank you for your business.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div style="margin-top:20px; font-size:11px; color:#9ca3af;">
                To print or save as PDF: press <strong>Ctrl+P</strong> (or Cmd+P on Mac),
                then choose <strong>Save as PDF</strong> as the destination.
            </div>
            """,
            unsafe_allow_html=True,
        )
