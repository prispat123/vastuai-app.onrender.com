from __future__ import annotations

import os
from typing import Any


def _st():
    import streamlit as st
    return st


def configured() -> bool:
    return bool(os.getenv("SUPABASE_URL", "").strip() and os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip())


def _new_client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.")
    return create_client(url, key)


def client():
    st = _st()
    if "_supabase_client" not in st.session_state:
        st.session_state["_supabase_client"] = _new_client()
    return st.session_state["_supabase_client"]


def current_user() -> Any | None:
    try:
        return _st().session_state.get("auth_user")
    except Exception:
        return None


def user_id() -> str | None:
    user = current_user()
    return str(user.id) if user is not None else None


def _store_auth(response: Any) -> None:
    st = _st()
    user = getattr(response, "user", None)
    session = getattr(response, "session", None)
    st.session_state.auth_user = user
    st.session_state.auth_session = session
    if user is not None:
        st.session_state.user_id = str(user.id)
        st.session_state.user_email = getattr(user, "email", "") or ""


def sign_in(email: str, password: str) -> None:
    response = client().auth.sign_in_with_password({"email": email.strip(), "password": password})
    _store_auth(response)
    if current_user() is None:
        raise RuntimeError("Sign in did not return a user.")


def sign_up(email: str, password: str, display_name: str) -> bool:
    response = client().auth.sign_up({
        "email": email.strip(),
        "password": password,
        "options": {"data": {"display_name": display_name.strip()}},
    })
    _store_auth(response)
    return getattr(response, "session", None) is not None


def sign_out() -> None:
    st = _st()
    try:
        if "_supabase_client" in st.session_state:
            st.session_state["_supabase_client"].auth.sign_out()
    finally:
        for key in [
            "_supabase_client", "auth_user", "auth_session", "user_id", "user_email",
            "workspace", "active_project_id", "selected_property_id", "selected_property_label",
        ]:
            st.session_state.pop(key, None)


def render_login_gate() -> bool:
    """Render authentication UI. Return True only for an authenticated session."""
    st = _st()
    if current_user() is not None:
        return True

    st.markdown("## Welcome to VastuAI")
    st.caption("Sign in to access your private Professional and Builder workspace.")

    if not configured():
        st.error(
            "Cloud authentication is not configured on this deployment. "
            "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the server environment."
        )
        st.stop()

    sign_in_tab, create_tab = st.tabs(["Sign in", "Create account"])

    with sign_in_tab:
        with st.form("vastuai_sign_in"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            try:
                sign_in(email, password)
                st.rerun()
            except Exception as exc:
                st.error(f"Sign in failed: {exc}")

    with create_tab:
        with st.form("vastuai_sign_up"):
            display_name = st.text_input("Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if submitted:
            if len(password) < 8:
                st.warning("Use a password with at least 8 characters.")
            elif password != confirm:
                st.warning("Passwords do not match.")
            elif not email.strip():
                st.warning("Enter an email address.")
            else:
                try:
                    signed_in = sign_up(email, password, display_name)
                    if signed_in:
                        st.success("Account created.")
                        st.rerun()
                    else:
                        st.success("Account created. Check your email to confirm the address, then sign in.")
                except Exception as exc:
                    st.error(f"Account creation failed: {exc}")

    st.info("Your VastuAI records are associated with your authenticated user ID.")
    return False
