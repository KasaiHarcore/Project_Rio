"""Authentication UI pages for Streamlit.

Provides login, registration, and password reset interfaces.
"""

import streamlit as st
from backend.application.services.auth_service import AuthService
from backend.infrastructure.dto.session import get_session
from backend.infrastructure.dto.models.user import UserRole


def render_login_page():
    """Render login page with Grok-style dark theme."""

    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'> Login to Agentic Chat</h1>", unsafe_allow_html=True)

    # Centered login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Sign In")
            username = st.text_input(
                "Username or Email",
                placeholder="Enter your username or email",
                help="Use your registered username or email address"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                help="Minimum 8 characters"
            )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                login_btn = st.form_submit_button("Login", use_container_width=True, type="primary")
            with col_btn2:
                register_btn = st.form_submit_button("Register", use_container_width=True)

            if login_btn:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    with st.spinner("Authenticating..."):
                        with get_session() as session:
                            success, user_data, tokens, error = AuthService.login(session, username, password)

                        if success:
                            # Store user info in session state
                            st.session_state.authenticated = True
                            st.session_state.show_register = False
                            st.session_state.show_reset_password = False
                            st.session_state.current_user = {
                                "id": str(user_data.id),
                                "username": user_data.username,
                                "email": user_data.email,
                                "role": user_data.role.value,
                                "created_at": user_data.created_at.isoformat()
                            }
                            # Store tokens for authenticated API calls
                            st.session_state.tokens = {
                                "access_token": tokens.access_token,
                                "refresh_token": tokens.refresh_token,
                            }
                            st.success(f"Welcome back, {user_data.username}!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"{error}")

            if register_btn:
                st.session_state.show_register = True
                st.rerun()

        # Forgot password link
        st.markdown("---")
        if st.button("Forgot Password?", use_container_width=True):
            st.session_state.show_reset_password = True
            st.rerun()

        # Info box
        with st.expander("First time here?"):
            st.info(
                "**New users**: Click 'Register' to create an account\n\n"
                "**Default admin credentials** (for testing):\n"
                "- Username: `admin`\n"
                "- Password: `admin12345`"
            )


def render_register_page():
    """Render registration page."""

    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>Create Account</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("register_form", clear_on_submit=True):
            st.markdown("### New User Registration")

            username = st.text_input(
                "Username",
                placeholder="Choose a unique username",
                help="3-255 characters, will be used for login"
            )
            email = st.text_input(
                "Email",
                placeholder="your.email@example.com",
                help="Valid email address required"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Create a strong password",
                help="Minimum 8 characters"
            )
            password_confirm = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Re-enter your password"
            )

            submit_btn = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if submit_btn:
                # Validation
                if not username or not email or not password or not password_confirm:
                    st.error("All fields are required")
                elif password != password_confirm:
                    st.error("Passwords do not match")
                elif len(username) < 3:
                    st.error("Username must be at least 3 characters")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters")
                elif "@" not in email:
                    st.error("Please enter a valid email address")
                else:
                    with st.spinner("Creating account..."):
                        with get_session() as session:
                            success, user_data, error = AuthService.register(
                                session, username, email, password, UserRole.USER
                            )

                        if success:
                            st.success(f"Account created successfully! Welcome, {username}!")
                            st.info("Please login with your new credentials.")
                            st.session_state.show_register = False
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"{error}")

        if st.button("Back to Login", use_container_width=True):
            st.session_state.show_register = False
            st.session_state.show_reset_password = False
            st.rerun()


def render_reset_password_page():
    """Render password reset page."""

    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>Reset Password</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("reset_form", clear_on_submit=True):
            st.markdown("### Password Recovery")
            st.info("For local deployment, enter your username/email and new password directly.")

            username_or_email = st.text_input(
                "Username or Email",
                placeholder="Enter your username or email"
            )
            new_password = st.text_input(
                "New Password",
                type="password",
                placeholder="Enter new password",
                help="Minimum 8 characters"
            )
            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                placeholder="Re-enter new password"
            )

            submit_btn = st.form_submit_button("Reset Password", use_container_width=True, type="primary")

            if submit_btn:
                if not username_or_email or not new_password or not confirm_password:
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    with st.spinner("Resetting password..."):
                        with get_session() as session:
                            success, error = AuthService.reset_password(
                                session, username_or_email, new_password
                            )

                        if success:
                            st.success("Password reset successfully!")
                            st.info("Please login with your new password.")
                            st.session_state.show_reset_password = False
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"{error}")

        if st.button("Back to Login", use_container_width=True):
            st.session_state.show_reset_password = False
            st.session_state.show_register = False
            st.rerun()


def render_auth_routing():
    """Main authentication routing logic.

    Returns:
        bool: True if authenticated, False otherwise
    """
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    if "show_reset_password" not in st.session_state:
        st.session_state.show_reset_password = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    if st.session_state.current_user and not st.session_state.authenticated:
        st.session_state.authenticated = True

    # If authenticated, return True to show main app
    if st.session_state.authenticated:
        return True

    # Show appropriate auth page
    if st.session_state.show_register:
        render_register_page()
    elif st.session_state.show_reset_password:
        render_reset_password_page()
    else:
        render_login_page()

    return False