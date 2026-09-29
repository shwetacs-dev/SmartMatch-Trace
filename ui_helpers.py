"""
ui_helpers.py
--------------
All visual/UX support code:
  - Per-page animated backgrounds (home / login / dashboard / report pages)
  - Floating icon + moving gradient animations
  - A readable "card" wrapper so busy backgrounds never fight with text
  - Status badges (colour-coded)
  - Image gallery with a main image + clickable thumbnails
  - Notification bell dropdown
  - Admin login gate
  - Chart rendering with a real hover tooltip (native browser tooltip)

Kept separate from app.py so the main file stays focused on page logic.
"""

import os
import io
import uuid
import base64
import streamlit as st

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "uploaded_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

STATUS_BADGES = {
    "Unclaimed":       ("⚪", "#9e9e9e"),
    "Possible Match":  ("🟡", "#f9a825"),
    "Pending":         ("🟡", "#f9a825"),
    "Under Verification": ("🔵", "#1e88e5"),
    "Claimed":         ("🟢", "#43a047"),
    "Verified":        ("🟢", "#43a047"),
    "Rejected":        ("🔴", "#e53935"),
    "Archived":        ("⚪", "#9e9e9e"),
}


# ---------------------------------------------------------------------------
# IMAGE HANDLING
# ---------------------------------------------------------------------------

def save_uploaded_images(uploaded_files):
    if not uploaded_files:
        return None
    saved_names = []
    for file in uploaded_files:
        ext = os.path.splitext(file.name)[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(IMAGES_DIR, unique_name)
        with open(filepath, "wb") as f:
            f.write(file.getbuffer())
        saved_names.append(unique_name)
    return ",".join(saved_names)


def display_image_gallery(image_paths_str, caption_prefix="", max_cols=4):
    """Simple row-of-columns gallery (used in compact contexts like Admin Panel)."""
    if not image_paths_str:
        return
    filenames = [f.strip() for f in image_paths_str.split(",") if f.strip()]
    if not filenames:
        return
    cols = st.columns(min(len(filenames), max_cols))
    for i, filename in enumerate(filenames):
        filepath = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(filepath):
            with cols[i % max_cols]:
                st.image(filepath, width="stretch",
                          caption=f"{caption_prefix} {i+1}".strip())


def display_image_carousel(image_paths_str, item_id, caption=""):
    """
    Main image + clickable thumbnail strip, approximating a carousel.
    Uses st.session_state to remember which thumbnail is selected per item.
    """
    if not image_paths_str:
        return

    filenames = [f.strip() for f in image_paths_str.split(",") if f.strip()]
    filenames = [f for f in filenames if os.path.exists(os.path.join(IMAGES_DIR, f))]
    if not filenames:
        return

    state_key = f"carousel_index_{item_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    current_index = min(st.session_state[state_key], len(filenames) - 1)
    main_path = os.path.join(IMAGES_DIR, filenames[current_index])
    st.image(main_path, width="stretch", caption=caption)

    if len(filenames) > 1:
        thumb_cols = st.columns(len(filenames))
        for i, filename in enumerate(filenames):
            with thumb_cols[i]:
                filepath = os.path.join(IMAGES_DIR, filename)
                st.image(filepath, width="stretch")
                is_current = (i == current_index)
                if st.button(
                    "●" if is_current else "○",
                    key=f"thumb_{item_id}_{i}",
                    width="stretch"
                ):
                    st.session_state[state_key] = i
                    st.rerun()


# ---------------------------------------------------------------------------
# STATUS BADGES
# ---------------------------------------------------------------------------

def status_badge_html(status):
    """Returns an inline-HTML colour-coded badge for a status string."""
    icon, color = STATUS_BADGES.get(status, ("⚪", "#9e9e9e"))
    return (
        f'<span style="background:{color}22; color:{color}; padding:3px 10px; '
        f'border-radius:999px; font-weight:600; font-size:0.85em; border:1px solid {color}55;">'
        f'{icon} {status}</span>'
    )


def render_status_badge(status):
    st.markdown(status_badge_html(status), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# EXPANDABLE ITEM CARD (compact list -> "View Details")
# ---------------------------------------------------------------------------

def render_item_card_header(item):
    """Compact one-line summary shown before the user expands for full details."""
    type_icon = "🔴" if item["type"] == "lost" else "🟢"
    st.markdown(
        f"**{item['item_name']}**  ·  📍 {item['location'] or '—'}  ·  "
        f"{type_icon} {item['type'].title()}  ·  {status_badge_html(item['status'])}",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# NOTIFICATIONS BELL
# ---------------------------------------------------------------------------

def render_notification_bell(user_id):
    """Renders a bell with unread count + expandable notification list."""
    import database as db

    unread = db.count_unread_notifications(user_id)
    bell_label = f"🔔 Notifications ({unread} new)" if unread else "🔔 Notifications"

    with st.expander(bell_label):
        notifications = db.get_notifications_for_user(user_id)
        if not notifications:
            st.caption("No notifications yet.")
        else:
            for n in notifications:
                st.markdown(f"{n['icon']} {n['message']}  \n"
                            f"<span style='color:gray;font-size:0.8em;'>{n['created_at']}</span>",
                            unsafe_allow_html=True)
                st.markdown("---")
            if unread and st.button("Mark all as read", key=f"markread_{user_id}"):
                db.mark_all_notifications_read(user_id)
                st.rerun()


# ---------------------------------------------------------------------------
# ADMIN LOGIN GATE
# ---------------------------------------------------------------------------

def require_admin_login():
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if st.session_state.admin_logged_in:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("Log out", key="admin_logout_btn"):
                st.session_state.admin_logged_in = False
                st.rerun()
        return True

    st.subheader("🔐 Admin Login")
    st.caption("This area is restricted to authorized staff only.")

    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")

        if submitted:
            with st.spinner("Checking credentials..."):
                valid = (username == ADMIN_USERNAME and password == ADMIN_PASSWORD)
            if valid:
                st.session_state.admin_logged_in = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    return False


# ---------------------------------------------------------------------------
# CHART RENDERING WITH REAL HOVER TOOLTIPS
# ---------------------------------------------------------------------------

def render_chart_with_insight(fig, insight_text, width_pct=100):
    """
    Renders a matplotlib figure as an <img> with a native browser tooltip
    (the 'title' attribute) so hovering over the chart shows the insight --
    genuine hover behaviour without needing a JS charting library.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()

    safe_title = (insight_text or "").replace('"', "&quot;")
    html = (
        f'<div class="chart-card" title="{safe_title}">'
        f'<img src="data:image/png;base64,{encoded}" style="width:{width_pct}%; '
        f'border-radius:12px;" />'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    st.caption(f"💡 {insight_text}")


# ---------------------------------------------------------------------------
# PER-PAGE ANIMATED BACKGROUNDS & THEME
# ---------------------------------------------------------------------------

FLOATING_ICONS = ["🔑", "🎒", "🕶️", "📱", "📚", "☂️", "👛", "🧢"]


def _floating_icons_html(count=8):
    """Generates absolutely-positioned floating icons with varied animation
    timing, for a noticeable (but not distracting) motion effect."""
    spans = []
    for i in range(count):
        icon = FLOATING_ICONS[i % len(FLOATING_ICONS)]
        left = (i * 13) % 100
        duration = 14 + (i % 5) * 3
        delay = (i % 4) * 2
        size = 28 + (i % 3) * 10
        spans.append(
            f'<span class="floating-icon" style="left:{left}%; '
            f'animation-duration:{duration}s; animation-delay:-{delay}s; '
            f'font-size:{size}px;">{icon}</span>'
        )
    return f'<div class="floating-icons-container">{"".join(spans)}</div>'


BASE_CSS = """
<style>
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes floatDrift {
    0%   { transform: translateY(100vh) rotate(0deg); opacity: 0; }
    10%  { opacity: 0.35; }
    90%  { opacity: 0.35; }
    100% { transform: translateY(-10vh) rotate(25deg); opacity: 0; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

.floating-icons-container {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    overflow: hidden;
    z-index: 0;
    pointer-events: none;
}
.floating-icon {
    position: absolute;
    bottom: -60px;
    animation-name: floatDrift;
    animation-timing-function: ease-in-out;
    animation-iteration-count: infinite;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.15));
}

section.main > div.block-container {
    position: relative;
    z-index: 1;
    animation: fadeInUp 0.5s ease;
}

section.main > div.block-container {
    background: rgba(255, 255, 255, 0.82);
    backdrop-filter: blur(6px);
    border-radius: 20px;
    padding: 2rem 2.2rem !important;
    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #6a11cb 0%, #2575fc 100%);
}
section[data-testid="stSidebar"] * {
    color: white !important;
}

div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.85);
    border-radius: 14px;
    padding: 14px 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    transition: transform 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-4px) scale(1.02);
}

h1 { color: #4a148c; text-shadow: 1px 1px 2px rgba(0,0,0,0.05); }
h2, h3 { color: #6a1b9a; }

.stButton > button {
    border-radius: 10px;
    border: none;
    background: linear-gradient(90deg, #ff6a88, #ff99ac);
    color: white;
    font-weight: 600;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover {
    transform: scale(1.03);
    box-shadow: 0 4px 12px rgba(255, 106, 136, 0.5);
}

div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

.streamlit-expanderHeader {
    background: rgba(255,255,255,0.6);
    border-radius: 8px;
    font-weight: 600;
}

.chart-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 8px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    cursor: help;
    transition: transform 0.15s ease;
}
.chart-card:hover {
    transform: translateY(-3px);
}
</style>
"""

BACKGROUND_THEMES = {
    "home": "linear-gradient(-45deg, #a1c4fd, #fbc2eb, #fddb92, #84fab0)",
    "login": "linear-gradient(-45deg, #e0c3fc, #8ec5fc)",
    "dashboard": "linear-gradient(-45deg, #f5f7fa, #dfe9f3, #f5f7fa)",
    "analytics": "linear-gradient(-45deg, #f5f7fa, #dfe9f3, #f5f7fa)",
    "report": "linear-gradient(-45deg, #fdfbfb, #ebedee, #fdfbfb)",
    "default": "linear-gradient(-45deg, #d4fc79, #96e6a1, #a1c4fd, #c2e9fb)",
}


def apply_custom_theme(page_key="default", show_floating_icons=None):
    """
    Call once near the top of a page. page_key selects the background
    gradient; show_floating_icons defaults to True only for pages where
    lively motion won't interfere with reading data (home, login, report).
    """
    gradient = BACKGROUND_THEMES.get(page_key, BACKGROUND_THEMES["default"])

    if show_floating_icons is None:
        show_floating_icons = page_key in ("home", "login", "report")

    st.markdown(BASE_CSS, unsafe_allow_html=True)
    st.markdown(f"""
        <style>
        .stApp {{
            background: {gradient};
            background-size: 400% 400%;
            animation: gradientShift 18s ease infinite;
        }}
        </style>
    """, unsafe_allow_html=True)

    if show_floating_icons:
        st.markdown(_floating_icons_html(count=10), unsafe_allow_html=True)
