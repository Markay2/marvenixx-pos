import os

import pandas as pd
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Invoice / Pro Forma – Ateasefuor", layout="wide")
st.markdown("## 🧾 Invoice / Pro Forma")

sale_id = st.number_input("Sale ID", min_value=1, step=1, value=1)

if st.button("Load Sale"):
    try:
        r = requests.get(f"{API_BASE}/sales/{int(sale_id)}", timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        st.error(f"Error loading sale: {e}")
    else:
        # If backend returns a dict with sale + lines, try both shapes
        if "sale" in data:
            sale = data["sale"]
            lines = data.get("lines", [])
        else:
            # Flat shape: assume data is the sale, and maybe has "lines"
            sale = data
            lines = data.get("lines", [])

                # ---- Compute total from the line items ----
        total_from_lines = 0.0
        if lines:
            total_from_lines = sum(
                float(l.get("line_total", 0) or 0.0) for l in lines
            )

        st.markdown("### Invoice Details")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Sale ID:** {sale.get('id')}")
            st.write(f"**Customer:** {sale.get('customer_name', 'Walk-in')}")
        with col2:
            # You don't have location_id on Sale model yet, so this may be None
            st.write(f"**Location ID:** {sale.get('location_id', None)}")
            st.write(f"**Total:** ₵ {total_from_lines:.2f}")

        st.markdown("---")

        if lines:
            df = pd.DataFrame(lines)
            st.table(df)
        else:
            st.info("No line items found for this sale.")

        st.markdown("---")
        st.caption(
            "To print, use your browser's **Print** function (Ctrl+P / Cmd+P) "
            "and choose PDF or a physical printer."
        )
