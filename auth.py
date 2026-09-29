"""
auth.py
--------
Handles student account registration and login (separate from the admin
login in ui_helpers.py, which uses a single hardcoded staff account).

Passwords are hashed with SHA-256 before being stored -- never saved as
plain text. For a real production system you'd want a slower, salted
algorithm (like bcrypt), but SHA-256 is enough to demonstrate the concept
correctly for a college project: the point being made is "don't store
plain text passwords", which this does satisfy.
"""

import hashlib
import re
import streamlit as st

import database as db

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_student(name, email, contact, password):
    """Returns (success: bool, message: str)."""
    if not name or not email or not password:
        return False, "Please fill in your name, email, and password."
    if not EMAIL_PATTERN.match(email):
        return False, "Please enter a valid email address."
    if len(password) < 4:
        return False, "Password should be at least 4 characters."

    existing = db.get_user_by_email(email)
    if existing:
        return False, "An account with this email already exists. Please log in instead."

    user_id = db.create_user(name, email, contact, hash_password(password))
    if user_id is None:
        return False, "An account with this email already exists. Please log in instead."
    return True, "Account created successfully! You can now log in."


def login_student(email, password):
    """Returns (success: bool, message: str). On success, also sets session state."""
    user = db.get_user_by_email(email)
    if user is None:
        return False, "No account found with that email. Please register first."

    if user["password_hash"] != hash_password(password):
        return False, "Incorrect password."

    st.session_state.student_logged_in = True
    st.session_state.student_user = dict(user)
    return True, "Login successful!"


def logout_student():
    st.session_state.student_logged_in = False
    st.session_state.student_user = None


def is_student_logged_in():
    return st.session_state.get("student_logged_in", False)


def current_student():
    """Returns the logged-in student's user dict, or None."""
    return st.session_state.get("student_user")


def render_login_register_form():
    """
    Renders a Login / Register tabbed form. Returns True once the student
    is logged in (so calling pages can gate content behind this).
    """
    if is_student_logged_in():
        return True

    st.subheader("🎓 Student Login")

    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    with tab_login:
        with st.form("student_login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
            if submitted:
                with st.spinner("Logging in..."):
                    success, message = login_student(email, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with tab_register:
        with st.form("student_register_form"):
            name = st.text_input("Full Name")
            email_r = st.text_input("Email", key="reg_email")
            contact = st.text_input("Contact Number")
            password_r = st.text_input("Password", type="password", key="reg_password")
            submitted_r = st.form_submit_button("Create Account", use_container_width=True)
            if submitted_r:
                with st.spinner("Creating your account..."):
                    success, message = register_student(name, email_r, contact, password_r)
                if success:
                    st.success(message)
                else:
                    st.error(message)

    return False
