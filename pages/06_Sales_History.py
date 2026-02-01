# app/pages/06_Sales_History.py

import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

from auth import require_login

require_login()

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Sales History – Ateasefuor", layout="wide")
st.markdown("## 🧾 Sales History")


# -------------------- Helpers --------------------
def api_get(path: str, params=None, timeout=15):
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict, timeout=20):
    r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def money(x) -> str:
    try:
        return f"₵ {float(x):,.2f}"
    except Exception:
        return "₵ 0.00"


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


# -------------------- Filters --------------------
col_from, col_to, col_refresh = st.columns([1, 1, 0.8])
with col_from:
    start_date = st.date_input("From date", value=date.today().replace(day=1))
with col_to:
    end_date = st.date_input("To date", value=date.today())
with col_refresh:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if start_date > end_date:
    st.error("From date cannot be after To date.")
    st.stop()


# -------------------- Loaders --------------------
@st.cache_data(ttl=60)
def load_sales(start_date: date, end_date: date):
    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "limit": 1000,
    }
    return api_get("/sales/history", params=params, timeout=20)


@st.cache_data(ttl=60)
def load_sale(sale_id: int):
    return api_get(f"/sales/{int(sale_id)}", timeout=20)


@st.cache_data(ttl=120)
def load_products():
    data = api_get("/products", timeout=20)
    return data if isinstance(data, list) else []


# -------------------- Main Layout --------------------
left, right = st.columns([1.25, 1], gap="large")

# ================= LEFT: list =================
with left:
    try:
        data = load_sales(start_date, end_date)
    except Exception as e:
        st.error(f"Could not load sales history: {e}")
        st.stop()

    if not data:
        st.info("No sales for this period.")
        st.stop()

    df = pd.DataFrame(data)

    # Normalize types
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if "total" in df.columns:
        df["total"] = df["total"].apply(lambda v: safe_float(v, 0.0))

    # Display table nicely
    display_cols = []
    for c in ["id", "receipt_no", "created_at", "customer_name", "location_id", "total"]:
        if c in df.columns:
            display_cols.append(c)

    df_view = df[display_cols].copy()
    if "created_at" in df_view.columns:
        df_view["created_at"] = df_view["created_at"].dt.strftime("%Y-%m-%d %H:%M")

    # rename
    rename_map = {
        "id": "Sale ID",
        "receipt_no": "Receipt No",
        "created_at": "Date/Time",
        "customer_name": "Customer",
        "location_id": "Location ID",
        "total": "Total",
    }
    df_view = df_view.rename(columns=rename_map)

    st.markdown("### Sales list")
    st.dataframe(df_view, use_container_width=True, hide_index=True)

    # Sale selector (for details panel)
    df = df.sort_values("id", ascending=False)

    def label_row(r):
        sid = int(r.get("id") or 0)
        rno = str(r.get("receipt_no") or "").strip()
        cust = str(r.get("customer_name") or "Walk-in").strip()
        when = ""
        if pd.notna(r.get("created_at")):
            when = pd.to_datetime(r["created_at"]).strftime("%Y-%m-%d %H:%M")
        total = money(r.get("total", 0))
        if rno:
            return f"{sid} • {rno} • {when} • {cust} • {total}"
        return f"{sid} • {when} • {cust} • {total}"

    df["label"] = df.apply(label_row, axis=1)
    label_to_id = {row["label"]: int(row["id"]) for _, row in df.iterrows()}

    default_sale_id = int(st.session_state.get("selected_sale_id") or int(df["id"].iloc[0]))
    default_label = next((lb for lb, sid in label_to_id.items() if sid == default_sale_id), df["label"].iloc[0])

    chosen = st.selectbox("Select a sale to view/edit", df["label"].tolist(), index=df["label"].tolist().index(default_label))
    selected_sale_id = label_to_id[chosen]
    st.session_state["selected_sale_id"] = selected_sale_id


# ================= RIGHT: details + add lines =================
with right:
    st.markdown("### Sale details & add products")

    sale_id = int(st.session_state.get("selected_sale_id") or 0)
    if not sale_id:
        st.info("Select a sale first.")
        st.stop()

    try:
        detail = load_sale(sale_id)
        sale = detail.get("sale") or {}
        lines = detail.get("lines") or []
    except Exception as e:
        st.error(f"Could not load sale #{sale_id}: {e}")
        st.stop()

    receipt_no = str(sale.get("receipt_no") or "").strip()
    customer = str(sale.get("customer_name") or "Walk-in Customer").strip() or "Walk-in Customer"
    created_at = str(sale.get("created_at") or "")
    location_id = sale.get("location_id", None)

    st.write(f"**Sale ID:** {sale.get('id', sale_id)}")
    if receipt_no:
        st.write(f"**Receipt No:** {receipt_no}")
    st.write(f"**Customer:** {customer}")
    st.write(f"**Created:** {created_at}")
    st.write(f"**Location ID:** {location_id}")

    # Show line items
    st.markdown("#### Items sold")
    if lines:
        dfl = pd.DataFrame(lines)
        if "product_name" not in dfl.columns and "name" in dfl.columns:
            dfl["product_name"] = dfl["name"]

        for c in ["qty", "unit_price", "line_total"]:
            if c in dfl.columns:
                dfl[c] = dfl[c].apply(lambda v: safe_float(v, 0.0))

        view_cols = [c for c in ["sku", "product_name", "qty", "unit_price", "line_total"] if c in dfl.columns]
        dshow = dfl[view_cols].rename(
            columns={
                "sku": "SKU",
                "product_name": "Item",
                "qty": "Qty",
                "unit_price": "Unit Price",
                "line_total": "Line Total",
            }
        )
        st.dataframe(dshow, use_container_width=True, hide_index=True)
    else:
        st.info("No line items found.")

    total = safe_float(sale.get("total") or sale.get("total_amount") or 0.0, 0.0)
    st.markdown(f"### Current total: {money(total)}")

    st.markdown("---")
    st.markdown("### Add new products to this sale (without deleting old ones)")

    # Add-lines UI requires your API endpoint: POST /sales/{sale_id}/add_lines
    # (You already added it in your sales router.)

    products = load_products()
    if not products:
        st.info("No products available.")
        st.stop()

    pdf = pd.DataFrame(products)
    for c in ["sku", "name", "unit", "selling_price"]:
        if c not in pdf.columns:
            pdf[c] = None

    pdf["selling_price"] = pdf["selling_price"].apply(lambda v: safe_float(v, 0.0))
    pdf["label"] = pdf.apply(lambda r: f"{str(r['name'] or '').strip()} ({str(r['sku'] or '').strip()}) • {money(r['selling_price'])}", axis=1)
    label_to_row = {r["label"]: r for _, r in pdf.iterrows() if str(r.get("sku") or "").strip()}

    chosen_prod = st.selectbox("Product", list(label_to_row.keys()))
    pr = label_to_row[chosen_prod]

    sku = str(pr.get("sku") or "").strip()
    default_price = safe_float(pr.get("selling_price"), 0.0)

    c1, c2 = st.columns(2)
    with c1:
        qty = st.number_input("Qty", min_value=0.0, value=1.0, step=0.5, format="%.3f")
    with c2:
        unit_price = st.number_input("Unit price", min_value=0.0, value=float(default_price), step=0.1)

    # Location to deduct stock from (default is sale location)
    loc_default = int(location_id) if location_id else 1
    loc_for_add = st.number_input("Location ID for stock deduction", min_value=1, step=1, value=loc_default)

    if st.button("✅ Add to sale", use_container_width=True):
        if not sku:
            st.error("Product SKU missing.")
        elif qty <= 0:
            st.error("Qty must be > 0")
        else:
            try:
                payload = {
                    "location_id": int(loc_for_add),
                    "lines": [{"sku": sku, "qty": float(qty), "unit_price": float(unit_price)}],
                }
                res = api_post(f"/sales/{int(sale_id)}/add_lines", payload, timeout=25)
                st.success(f"Added. New total: {money(res.get('new_total', 0))}")
                st.cache_data.clear()
                st.rerun()
            except requests.HTTPError as e:
                try:
                    st.error(e.response.text)
                except Exception:
                    st.error(str(e))
            except Exception as e:
                st.error(f"Error: {e}")
