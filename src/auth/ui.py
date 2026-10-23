"""Streamlit login / signup screen that gates access to the main dashboard."""

import streamlit as st

from src.auth.database import (
    authenticate_user,
    create_user,
    get_user_role,
    init_user_db,
)
from src.auth.notifications import send_auth_notifications
from src.config import DEFAULT_ROLE


def _init_session_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_name" not in st.session_state:
        st.session_state.user_name = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None


def is_authenticated() -> bool:
    _init_session_state()
    return st.session_state.authenticated


def current_role() -> str:
    """The signed-in user's role ('user' | 'admin' | 'department')."""
    _init_session_state()
    return st.session_state.user_role or DEFAULT_ROLE


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.session_state.user_role = None


def _handle_login(email: str, password: str) -> None:
    if not email or not password:
        st.error("Please enter both email and password.")
        return

    success, message = authenticate_user(email, password)
    if success:
        st.session_state.authenticated = True
        st.session_state.user_email = email.strip().lower()
        st.session_state.user_name = email.split("@")[0]
        st.session_state.user_role = get_user_role(email.strip().lower())

        warnings = send_auth_notifications("login", st.session_state.user_name, email)
        if warnings:
            st.session_state["_notify_warning"] = "; ".join(warnings)

        st.success(message)
        st.rerun()
    else:
        st.error(message)


def _handle_signup(full_name: str, email: str, password: str, confirm_password: str) -> None:
    if not full_name or not email or not password:
        st.error("Please fill in all fields.")
        return
    if password != confirm_password:
        st.error("Passwords do not match.")
        return
    if len(password) < 6:
        st.error("Password must be at least 6 characters long.")
        return

    success, message = create_user(full_name, email, password)
    if success:
        st.session_state.authenticated = True
        st.session_state.user_email = email.strip().lower()
        st.session_state.user_name = full_name.strip()
        st.session_state.user_role = DEFAULT_ROLE

        warnings = send_auth_notifications("signup", full_name, email)
        if warnings:
            st.session_state["_notify_warning"] = "; ".join(warnings)

        st.success(message)
        st.rerun()
    else:
        st.error(message)


def render_auth_page() -> None:
    """Render the login/signup page. Call this and stop further rendering
    (i.e. don't render the main app) until is_authenticated() is True."""
    _init_session_state()
    init_user_db()

    st.set_page_config(
        page_title="Pahad Guard — Sign In",
        page_icon="🏔️",
        layout="centered",
    )

    st.title("🏔️ Pahad Guard")
    st.caption("Sign in or create an account to access the landslide risk dashboard.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            _handle_login(email, password)

        st.caption(
            "Demo logins: admin@pahadguard.com · department@pahadguard.com · "
            "user@pahadguard.com (passwords in the README)"
        )

    with signup_tab:
        with st.form("signup_form"):
            full_name = st.text_input("Full name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input(
                "Confirm password", type="password", key="signup_confirm_password"
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)

        if submitted:
            _handle_signup(full_name, email, password, confirm_password)

        st.caption(
            "New accounts are created with the **User** role. An administrator "
            "can upgrade them from the Database page."
        )

    warning = st.session_state.pop("_notify_warning", None)
    if warning:
        st.info(
            f"Signed in, but the email notification could not be sent ({warning}). "
            "Check your Brevo configuration in .env."
        )
