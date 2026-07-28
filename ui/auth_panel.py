from __future__ import annotations

import streamlit as st

from core.session import (
    clear_user_session_state,
)
from core.user_context import UserContext


def render_login_screen() -> None:
    """Render the protected application entry screen."""

    st.title("TechCorp AI")
    st.subheader(
        "Secure, local-first AI workspace"
    )

    st.write(
        "Sign in to access your chats, documents, "
        "memories and AI tools."
    )

    with st.container(border=True):
        st.markdown(
            "### Sign in or create an account"
        )

        st.write(
            "Auth0 manages Google login, "
            "email/password accounts, account "
            "verification and password recovery."
        )

        if st.button(
            "Continue with Auth0",
            type="primary",
            use_container_width=True,
            key="auth0_login_button",
        ):
            st.login("auth0")

    st.caption(
        "Your Ollama models continue to run locally."
    )


def require_authenticated_user(
) -> UserContext:
    """
    Stop the application before backend startup unless
    an authenticated identity is available.
    """

    is_logged_in = bool(
        getattr(
            st.user,
            "is_logged_in",
            False,
        )
    )

    if not is_logged_in:
        render_login_screen()
        st.stop()

        raise RuntimeError(
            "Authentication flow stopped unexpectedly."
        )

    claims = (
        st.user.to_dict()
        if hasattr(st.user, "to_dict")
        else dict(st.user)
    )

    try:
        return UserContext.from_claims(
            claims
        )

    except ValueError as exc:
        st.error(
            "The login succeeded, but the identity "
            "information was incomplete."
        )

        st.caption(str(exc))

        if st.button(
            "Log out and try again",
            type="primary",
            key="invalid_identity_logout",
        ):
            clear_user_session_state()
            st.logout()

        st.stop()
        raise


def render_user_account(
    user: UserContext,
) -> None:
    """Render the authenticated account controls."""

    with st.sidebar:
        st.markdown("### Account")

        avatar_column, details_column = (
            st.columns([1, 4])
        )

        with avatar_column:
            if user.avatar_url:
                st.image(
                    user.avatar_url,
                    width=42,
                )

            else:
                st.markdown("## 👤")

        with details_column:
            st.markdown(
                f"**{user.name}**"
            )

            if user.email:
                st.caption(user.email)

        verification_status = (
            "Email verified"
            if user.email_verified
            else "Email verification not confirmed"
        )

        st.caption(verification_status)

        if st.button(
            "Log out",
            use_container_width=True,
            key="auth_logout_button",
        ):
            clear_user_session_state()
            st.logout()

        st.caption(
            "Authentication is active. Per-user data "
            "isolation will be added in the next phase."
        )

        st.divider()
