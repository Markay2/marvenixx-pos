# app/Home.py
import streamlit as st
from auth import check_credentials, set_login

st.set_page_config(
    page_title="MXP Login",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Hide sidebar + Streamlit chrome on login screen
st.markdown(
    """
    <style>
    [data-testid="stSidebar"], header, footer, #MainMenu { display:none !important; }
    .block-container { padding-top: 40px; max-width: 520px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# If already logged in -> go dashboard
if st.session_state.get("user"):
    st.switch_page("pages/00_Dashboard.py")

st.markdown("## 🔐 Marvenixx POS (MXP)")
st.caption("Log in to access the platform")

with st.form("login_form"):
    username = st.text_input("Username", placeholder="admin")
    password = st.text_input("Password", type="password", placeholder="admin123")
    remember = st.checkbox("Remember me", value=True, key="remember_me")  # key avoids warning
    submitted = st.form_submit_button("Login", use_container_width=True)

if submitted:
    ok, user_obj = check_credentials(username, password)
    if ok:
        set_login(user_obj, remember=remember)
        st.success("Login successful.")
        st.switch_page("pages/00_Dashboard.py")
    else:
        st.error("Invalid username or password.")
