# app/auth.py
import streamlit as st

USERS = {
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
    "cashier": {"username": "cashier", "password": "cashier123", "role": "user"},
}

def check_credentials(username: str, password: str):
    u = (username or "").strip().lower()
    p = (password or "").strip()
    user = USERS.get(u)
    if user and user["password"] == p:
        return True, {"username": user["username"], "role": user["role"]}
    return False, None

def set_login(user_obj: dict, remember: bool = True):
    st.session_state["user"] = user_obj
    st.session_state["remember"] = bool(remember)

def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("remember", None)

def require_login():
    if not st.session_state.get("user"):
        st.switch_page("Home.py")
