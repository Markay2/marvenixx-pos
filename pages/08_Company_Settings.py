import os
import base64
import requests
import streamlit as st

from auth import require_login
require_login()

API_BASE = os.getenv("API_BASE", "http://api:8000")

st.set_page_config(page_title="Settings – MXP", layout="centered")
st.title("⚙️ Company Settings (Branding)")

# Admin-only (uses your session login role)
current_user = st.session_state.get("user") or {}
is_admin = current_user.get("role") == "admin"
if not is_admin:
    st.warning("Admin only.")
    st.stop()


def api_get(path: str):
    r = requests.get(f"{API_BASE}{path}", timeout=20)
    r.raise_for_status()
    return r.json()

def api_post(path: str, payload: dict):
    r = requests.post(f"{API_BASE}{path}", json=payload, timeout=25)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=30)
def load_settings():
    return api_get("/settings/company")

settings = load_settings()

st.caption("These details will appear on receipts / proforma / waybill prints.")

with st.form("company_settings_form"):
    company_name = st.text_input("Company name", value=settings.get("company_name", ""))
    address = st.text_area("Address", value=settings.get("address", ""), height=80)
    phone = st.text_input("Phone", value=settings.get("phone", ""))
    website = st.text_input("Website", value=settings.get("website", ""))
    footer = st.text_input("Receipt footer text", value=settings.get("footer", "Thank you for your business."))

    uploaded = st.file_uploader("Upload Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

    submitted = st.form_submit_button("💾 Save settings")

if submitted:
    logo_base64 = settings.get("logo_base64", "")

    if uploaded is not None:
        b = uploaded.read()
        logo_base64 = base64.b64encode(b).decode("utf-8")

    payload = {
        "company_name": company_name.strip(),
        "address": address.strip(),
        "phone": phone.strip(),
        "website": website.strip(),
        "footer": footer.strip(),
        "logo_base64": logo_base64,
    }

    api_post("/settings/company", payload)
    st.cache_data.clear()
    st.success("Saved. Go to POS and print again.")
    st.rerun()

# Preview logo
if settings.get("logo_base64"):
    try:
        img_bytes = base64.b64decode(settings["logo_base64"])
        st.image(img_bytes, width=150)
    except Exception:
        pass
