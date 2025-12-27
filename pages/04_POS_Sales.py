# app/pages/04_POS_Sales.py
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from auth import require_login

require_login()

st.set_page_config(page_title="POS – Marvenixx POS", layout="wide")

API_BASE = os.getenv("API_BASE", "http://api:8000")
DEFAULT_STEP = 0.5


# -------------------- Styling (compact UI + printing) --------------------
st.markdown(
    """
    <style>
      .mxp-card{
        border:1px solid #e5e7eb;
        border-radius:10px;
        padding:8px 10px;
        background:#fff;
        margin-bottom:8px;
      }
      .mxp-name{font-weight:900;font-size:13px;line-height:1.1;}
      .mxp-meta{font-size:11px;color:#6b7280;margin-top:2px;}
      .mxp-price{margin-top:6px;font-weight:900;font-size:12px;}
      .mxp-avail{font-size:11px;color:#0f766e;margin-top:2px;}
      .mxp-qty{
        text-align:center;
        font-weight:900;
        font-size:16px;
        padding-top:3px;
      }
      .mxp-tiles button { margin-top: 4px; }

      @media print {
        [data-testid="stSidebar"], header, footer, #MainMenu, [data-testid="stToolbar"] { display:none !important; }
        .no-print { display:none !important; }
        .block-container { padding-top: 0 !important; }
        @page { size: A4 portrait; margin: 10mm; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------- Helpers --------------------
def api_get(path: str, params=None):
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict):
    return requests.post(f"{API_BASE}{path}", json=payload, timeout=25)


def money(x) -> str:
    try:
        return f"₵ {float(x):,.2f}"
    except Exception:
        return "₵ 0.00"


def safe_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


def get_step_for_unit(unit: str) -> float:
    u = (unit or "").strip().lower()
    if u in ["kg", "g", "gram", "grams", "l", "litre", "liter", "ml"]:
        return 0.1
    if u in ["piece", "pcs", "box", "bag", "bottle", "sachet", "tin", "gallon"]:
        return 0.5
    return DEFAULT_STEP


def clamp_to_step(x: float, step: float) -> float:
    if step <= 0:
        return float(x)
    return round(float(x) / step) * step


@st.cache_data(ttl=60)
def load_company():
    try:
        r = requests.get(f"{API_BASE}/settings/company", timeout=15)
        r.raise_for_status()
        data = r.json() or {}
    except Exception:
        data = {}

    return {
        "company_name": data.get("company_name", "Marvenixx POS (MXP)"),
        "address": data.get("address", ""),
        "phone": data.get("phone", ""),
        "website": data.get("website", ""),
        "footer": data.get("footer", "Thank you for your business."),
        "logo_base64": data.get("logo_base64", "") or "",
    }


def parse_sale_response(data):
    sale = None
    lines = []

    if isinstance(data, dict) and "sale" in data:
        sale = data.get("sale") or {}
        lines = data.get("lines") or []
    elif isinstance(data, dict):
        sale = data
        lines = data.get("lines") or []
    else:
        sale = None
        lines = []

    if not isinstance(lines, list):
        lines = []

    return sale, lines


def build_print_html(company, doc_type, receipt_no, sale_id, created, customer, location_label, lines, total_amount):
    rows_html = ""
    if doc_type == "Waybill":
        for ln in lines:
            item = ln.get("product_name") or ""
            qty = safe_float(ln.get("qty", 0), 0.0)
            rows_html += f"""
              <tr>
                <td style="padding:6px 0;border-bottom:1px solid #eee;">{item}</td>
                <td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;">{qty:.2f}</td>
              </tr>
            """
        header_cols = """
          <tr>
            <th style="text-align:left;border-bottom:2px solid #111;padding-bottom:6px;">Item</th>
            <th style="text-align:right;border-bottom:2px solid #111;padding-bottom:6px;">Qty</th>
          </tr>
        """
    else:
        for ln in lines:
            item = ln.get("product_name") or ""
            qty = safe_float(ln.get("qty", 0), 0.0)
            unit_price = safe_float(ln.get("unit_price", 0), 0.0)
            line_total = safe_float(ln.get("line_total", qty * unit_price), qty * unit_price)
            rows_html += f"""
              <tr>
                <td style="padding:6px 0;border-bottom:1px solid #eee;">{item}</td>
                <td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;">{qty:.2f}</td>
                <td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;">{money(unit_price)}</td>
                <td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;">{money(line_total)}</td>
              </tr>
            """
        header_cols = """
          <tr>
            <th style="text-align:left;border-bottom:2px solid #111;padding-bottom:6px;">Item</th>
            <th style="text-align:right;border-bottom:2px solid #111;padding-bottom:6px;">Qty</th>
            <th style="text-align:right;border-bottom:2px solid #111;padding-bottom:6px;">Price</th>
            <th style="text-align:right;border-bottom:2px solid #111;padding-bottom:6px;">Total</th>
          </tr>
        """

    logo_html = ""
    if company.get("logo_base64"):
        logo_html = f"<img src='data:image/png;base64,{company['logo_base64']}' style='height:60px;object-fit:contain;' />"

    created_txt = str(created)[:19].replace("T", " ") if created else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = (company.get("footer") or "").strip() or "Thank you for your business."

    total_html = ""
    if doc_type != "Waybill":
        total_html = f"""
          <hr style="margin:10px 0;" />
          <div style="text-align:right;font-weight:900;font-size:14px;">
            TOTAL: {money(total_amount)}
          </div>
        """

    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <style>
        body {{ font-family: Arial, sans-serif; font-size: 12px; color:#111; margin:0; padding:0; background:#fff; }}
        .wrap {{ width: 80mm; max-width: 80mm; margin:0 auto; padding:10px; background:#fff; border:1px solid #e5e7eb; border-radius:8px; }}
        table {{ width:100%; border-collapse:collapse; font-size:11px; }}
        th,td {{ padding:4px 0; }}
        button {{ border:1px solid #111; background:#111; color:#fff; padding:6px 10px; border-radius:6px; cursor:pointer; font-weight:700; font-size:11px; }}
        .muted {{ color:#6b7280; }}
        @media print {{
          body {{ margin:0; }}
          .no-print {{ display:none !important; }}
          @page {{ size:auto; margin:5mm; }}
        }}
      </style>
    </head>
    <body>
      <div class="wrap">
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <div>{logo_html}</div>
          <div style="flex:1;">
            <div style="font-weight:900;font-size:16px;line-height:1.1;">{company.get('company_name','')}</div>
            <div class="muted" style="font-size:12px;margin-top:6px;font-weight:800;">{doc_type}</div>
          </div>
        </div>

        <hr style="margin:10px 0;" />

        <div style="display:flex;justify-content:space-between;gap:10px;">
          <div>
            <div><b>Customer:</b> {customer}</div>
            <div><b>Location:</b> {location_label}</div>
          </div>
          <div style="text-align:right;">
            <div><b>Receipt:</b> {receipt_no or "-"}</div>
            <div><b>Sale ID:</b> {sale_id}</div>
            <div><b>Date:</b> {created_txt}</div>
          </div>
        </div>

        <div style="margin-top:10px;">
          <table>
            {header_cols}
            {rows_html if rows_html else "<tr><td colspan='4' style='padding:8px 0;'>No line items</td></tr>"}
          </table>
        </div>

        {total_html}

        <div style="text-align:center;color:#6b7280;font-size:11px;margin-top:12px;">
          {footer}
        </div>

        <div class="no-print" style="margin-top:12px;text-align:center;">
          <button onclick="window.print()">🖨 Print</button>
        </div>
      </div>
    </body>
    </html>
    """
    return html


# -------------------- Title + Top Controls --------------------
st.markdown("## 🧾 Point of Sale")

# Load locations
try:
    locs = api_get("/locations")
except Exception as e:
    st.error(f"Could not load locations: {e}")
    st.stop()

if not locs:
    st.warning("No locations found. Create locations first in the backend.")
    st.stop()

loc_labels = [f"{l['name']} (ID {l['id']})" for l in locs]
loc_map = {f"{l['name']} (ID {l['id']})": int(l["id"]) for l in locs}

top_a, top_b = st.columns([2, 1])
with top_a:
    location_label = st.selectbox("Sell from location", loc_labels, key="pos_location")
    location_id = loc_map[location_label]
with top_b:
    doc_type = st.selectbox("Print document", ["Receipt", "Proforma", "Waybill"], key="pos_doc_type")


@st.cache_data(ttl=10)
def load_products_with_stock(location_id: int):
    try:
        data = api_get("/products/with_stock", params={"location_id": location_id})
        if isinstance(data, list):
            return data
    except Exception:
        pass

    data = api_get("/products")
    if isinstance(data, list):
        for p in data:
            p["available_qty"] = None
        return data
    return []


try:
    products = load_products_with_stock(location_id)
except Exception as e:
    st.error(f"Could not load products: {e}")
    st.stop()

df = pd.DataFrame(products)
if df.empty:
    st.warning("No products found yet. Create products first (Products page).")
    st.stop()

for col in ["sku", "name", "unit", "selling_price", "available_qty"]:
    if col not in df.columns:
        df[col] = None

# Stock map for oversell checks
stock_map = {}
for _, r in df.iterrows():
    sku = str(r.get("sku") or "").strip()
    if not sku:
        continue
    stock_map[sku] = {
        "available_qty": safe_float(r.get("available_qty"), None),
        "unit": str(r.get("unit") or ""),
        "name": str(r.get("name") or ""),
        "selling_price": safe_float(r.get("selling_price"), 0.0),
    }


# -------------------- Cart State --------------------
if "cart" not in st.session_state:
    st.session_state["cart"] = []

if "last_sale_id" not in st.session_state:
    st.session_state["last_sale_id"] = None

if "print_now" not in st.session_state:
    st.session_state["print_now"] = False

# ✅ Add Panel state (REPLACES popover)
if "add_panel_sku" not in st.session_state:
    st.session_state["add_panel_sku"] = None

if "add_panel_qty" not in st.session_state:
    st.session_state["add_panel_qty"] = 0.0


def cart_find(sku: str):
    return next((x for x in st.session_state.get("cart", []) if x["sku"] == sku), None)


def cart_add_qty(sku: str, name: str, unit: str, unit_price: float, available_qty, qty_to_add: float):
    if not sku:
        return

    step = get_step_for_unit(unit)
    qty_to_add = clamp_to_step(max(0.0, float(qty_to_add)), step)
    if qty_to_add <= 0:
        return

    cart = st.session_state.get("cart", [])
    existing = cart_find(sku)
    already = safe_float(existing["qty"], 0.0) if existing else 0.0

    avail_f = safe_float(available_qty, None)
    if avail_f is not None and already + qty_to_add > avail_f:
        st.warning(f"Not enough stock. Available: {avail_f:.2f} {unit}")
        return

    if existing:
        existing["qty"] = clamp_to_step(already + qty_to_add, step)
    else:
        cart.append({"sku": sku, "name": name, "unit": unit, "qty": qty_to_add, "unit_price": float(unit_price)})

    st.session_state["cart"] = cart


def cart_set_qty(sku: str, qty: float):
    cart = st.session_state.get("cart", [])
    line = cart_find(sku)
    if not line:
        return

    unit = line.get("unit", "")
    step = get_step_for_unit(unit)
    new_qty = clamp_to_step(max(0.0, float(qty)), step)

    avail_f = stock_map.get(sku, {}).get("available_qty", None)
    if avail_f is not None and new_qty > avail_f:
        st.warning(f"Not enough stock for {line.get('name','')} — Available: {avail_f:.2f} {unit}")
        new_qty = avail_f

    if new_qty <= 0:
        st.session_state["cart"] = [x for x in cart if x["sku"] != sku]
    else:
        line["qty"] = float(new_qty)
        st.session_state["cart"] = cart


def cart_minus(sku: str):
    cart = st.session_state.get("cart", [])
    existing = cart_find(sku)
    if not existing:
        return

    unit = existing.get("unit", "")
    step = get_step_for_unit(unit)
    new_qty = clamp_to_step(max(0.0, safe_float(existing["qty"], 0.0) - step), step)

    if new_qty <= 0:
        st.session_state["cart"] = [x for x in cart if x["sku"] != sku]
    else:
        existing["qty"] = new_qty
        st.session_state["cart"] = cart


def cart_plus(sku: str):
    line = cart_find(sku)
    if not line:
        return
    unit = line.get("unit", "")
    step = get_step_for_unit(unit)
    cart_add_qty(
        sku=sku,
        name=line.get("name", ""),
        unit=unit,
        unit_price=float(line.get("unit_price", 0.0)),
        available_qty=stock_map.get(sku, {}).get("available_qty", None),
        qty_to_add=float(step),
    )


def cart_remove(sku: str):
    st.session_state["cart"] = [x for x in st.session_state.get("cart", []) if x["sku"] != sku]


# -------------------- Layout --------------------
left, right = st.columns([1.15, 1.85], gap="large")

# ================= LEFT: CART =================
with left:
    st.markdown("### 🛒 Current Sale")
    customer_name = st.text_input("Customer (optional)", key="pos_customer")

    cart = st.session_state["cart"]
    if not cart:
        st.info("Cart is empty. Add products on the right.")
    else:
        total = 0.0
        for line in list(cart):
            sku = str(line["sku"])
            unit = str(line.get("unit") or "")
            step = get_step_for_unit(unit)

            qty = safe_float(line.get("qty"), 0.0)
            price = safe_float(line.get("unit_price"), 0.0)

            st.markdown(
                f"""
                <div class="mxp-card">
                  <div class="mxp-name">{line['name']}</div>
                  <div class="mxp-meta">{unit} • SKU: {sku}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3, c4 = st.columns([1, 1.4, 1, 0.8], gap="small")

            if c1.button("➖", key=f"minus_{sku}", use_container_width=True):
                cart_minus(sku)
                st.rerun()

            with c2:
                typed_qty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    value=float(qty),
                    step=float(step),
                    format="%.3f",
                    key=f"qty_input_{sku}",
                    label_visibility="collapsed",
                )
                if float(typed_qty) != float(qty):
                    cart_set_qty(sku, float(typed_qty))
                    st.rerun()

            if c3.button("➕", key=f"plus_{sku}", use_container_width=True):
                cart_plus(sku)
                st.rerun()

            if c4.button("🗑", key=f"rm_{sku}", use_container_width=True):
                cart_remove(sku)
                st.rerun()

            line_now = cart_find(sku)
            if line_now:
                qty_now = safe_float(line_now.get("qty"), 0.0)
                price_now = safe_float(line_now.get("unit_price"), 0.0)
                line_total = qty_now * price_now
                total += line_total
                st.caption(f"{money(price_now)} each • Line: {money(line_total)}")

        st.markdown(f"### Total: {money(total)}")

        p1, p2, p3, p4 = st.columns(4)
        pay_cash = p1.button("💵 Cash", use_container_width=True)
        pay_card = p2.button("💳 Card", use_container_width=True)
        pay_momo = p3.button("📱 MoMo", use_container_width=True)

        if p4.button("🗑 Clear All", use_container_width=True):
            st.session_state["cart"] = []
            st.rerun()

        if pay_cash or pay_card or pay_momo:
            method = "CASH" if pay_cash else ("CARD" if pay_card else "MOMO")

            payload = {
                "customer_name": (customer_name or None),
                "location_id": int(location_id),
                "payment_method": method,
                "lines": [
                    {"sku": ln["sku"], "qty": float(ln["qty"]), "unit_price": float(ln["unit_price"])}
                    for ln in st.session_state["cart"]
                ],
            }

            r = api_post("/sales", payload)

            if r.status_code == 200:
                data = r.json() or {}
                sale_id = int(data.get("sale_id") or data.get("id") or 0)
                receipt_no = data.get("receipt_no")

                st.session_state["last_sale_id"] = sale_id
                st.session_state["cart"] = []
                st.session_state["print_now"] = False

                st.success(f"Sale #{sale_id} ({receipt_no}) recorded. Total {money(data.get('total', total))}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Error: {r.status_code} – {r.text}")


# ================= RIGHT: PRODUCTS =================
with right:
    st.markdown("### 📦 Products")
    search = st.text_input("Search product name / SKU", key="pos_search")

    # ✅ Add Panel (reliable replacement for popover)
    if st.session_state["add_panel_sku"]:
        sku = st.session_state["add_panel_sku"]
        info = stock_map.get(sku, {})
        name = info.get("name", sku)
        unit = info.get("unit", "")
        price = info.get("selling_price", 0.0)
        avail = info.get("available_qty", None)
        step = get_step_for_unit(unit)

        st.markdown("#### ➕ Add Quantity")
        a1, a2, a3, a4 = st.columns([2.2, 1.2, 1.2, 1.2], gap="small")

        with a1:
            st.info(f"**{name}** • SKU {sku} • {unit} • Price {money(price)}")

        with a2:
            qty_to_add = st.number_input(
                "Qty to add",
                min_value=0.0,
                value=float(st.session_state.get("add_panel_qty", step) or step),
                step=float(step),
                format="%.3f",
                key="add_panel_qty_input",
            )

        with a3:
            if st.button("✅ Add to Cart", use_container_width=True):
                cart_add_qty(
                    sku=sku,
                    name=name,
                    unit=unit,
                    unit_price=float(price),
                    available_qty=avail,
                    qty_to_add=float(qty_to_add),
                )
                st.session_state["add_panel_sku"] = None
                st.session_state["add_panel_qty"] = 0.0
                st.rerun()

        with a4:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state["add_panel_sku"] = None
                st.session_state["add_panel_qty"] = 0.0
                st.rerun()

        st.markdown("---")

    show_df = df.copy()
    if search:
        show_df = show_df[
            show_df["name"].astype(str).str.contains(search, case=False, na=False)
            | show_df["sku"].astype(str).str.contains(search, case=False, na=False)
        ]

    if show_df.empty:
        st.warning("No products match your search.")
    else:
        st.markdown('<div class="mxp-tiles">', unsafe_allow_html=True)

        cols = st.columns(3, gap="small")
        for i, (_, row) in enumerate(show_df.iterrows()):
            col = cols[i % 3]
            with col:
                name = str(row.get("name") or "")
                sku = str(row.get("sku") or "")
                unit = str(row.get("unit") or "")
                price = safe_float(row.get("selling_price"), 0.0)
                avail = row.get("available_qty", None)

                avail_txt = "—"
                if avail is not None:
                    af = safe_float(avail, None)
                    avail_txt = f"{af:.2f}" if af is not None else str(avail)

                st.markdown(
                    f"""
                    <div class="mxp-card" style="min-height:92px;">
                      <div class="mxp-name">{name}</div>
                      <div class="mxp-meta">SKU: {sku} • {unit}</div>
                      <div class="mxp-price">{money(price)}</div>
                      <div class="mxp-avail">Available: {avail_txt}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # ✅ Reliable Add button -> opens Add Panel
                if st.button("➕ Add", key=f"open_add_{sku}", use_container_width=True):
                    st.session_state["add_panel_sku"] = sku
                    st.session_state["add_panel_qty"] = get_step_for_unit(unit)
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ================= PRINT AREA =================
st.markdown("---")
st.markdown("## 🖨 Print Area")

sale_id = st.session_state.get("last_sale_id")
company = load_company()

if not sale_id:
    st.info("Complete a sale first. After payment, your document will appear here.")
else:
    sale = None
    lines = []

    try:
        data = api_get(f"/sales/{int(sale_id)}")
        sale, lines = parse_sale_response(data)
    except Exception as e:
        st.error(f"Could not load sale #{sale_id} for printing: {e}")
        sale = None
        lines = []

    controls = st.container()
    with controls:
        st.markdown('<div class="no-print">', unsafe_allow_html=True)
        cpa, cpb, cpc = st.columns([1, 1, 1])
        if cpa.button("🖨 Print Now", use_container_width=True):
            st.session_state["print_now"] = True
            st.rerun()
        if cpb.button("Clear last sale", use_container_width=True):
            st.session_state["last_sale_id"] = None
            st.session_state["print_now"] = False
            st.rerun()
        if cpc.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if sale:
        created = sale.get("created_at") or ""
        customer = sale.get("customer_name") or "Walk-in Customer"
        total_amount = sale.get("total") or sale.get("total_amount") or 0
        receipt_no = sale.get("receipt_no") or ""

        html = build_print_html(
            company=company,
            doc_type=doc_type,
            receipt_no=receipt_no,
            sale_id=sale.get("id", sale_id),
            created=created,
            customer=customer,
            location_label=location_label,
            lines=lines,
            total_amount=total_amount,
        )
        if st.session_state.get("print_now"):

            html = html.replace("</body>", "<script>window.print();</script></body>")
            st.session_state["print_now"] = False

        st.components.v1.html(html, height=740, scrolling=True)
    else:
        st.warning("No sale data returned. Please try again or check the sale id.")
