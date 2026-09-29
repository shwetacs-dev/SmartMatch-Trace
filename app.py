"""
app.py
-------
Main Streamlit application for the Lost & Found Management System.

Run with:
    streamlit run app.py

Flow:
  1. User lands on a role-selection screen (Student / Admin).
  2. Student → login/register → student sidebar & pages.
  3. Admin  → admin login     → admin   sidebar & pages.
  4. Either role can log out, which returns to the role-selection screen.
"""

import sys
import os

# Ensure all imports resolve from THIS project folder, not any other
# lost_found_system copy that might exist elsewhere on the Desktop.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# Remove any other desktop project folders from sys.path to avoid
# accidentally importing stale modules from old copies.
sys.path = [p for p in sys.path if not (
    p != _HERE and
    os.path.exists(os.path.join(p, "analytics.py")) and
    p != _HERE
)]

import streamlit as st
import pandas as pd
from datetime import date

import database as db
import auth
import match_engine
import analytics
import charts
import chart_insights
import ui_helpers
import claim_receipt
import qr_code

# ---------------------------------------------------------------------------
# PAGE CONFIG & INITIAL SETUP
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SmartMatch Trace",
    page_icon="🔎",
    layout="wide"
)

db.init_db()

CATEGORIES = ["Electronics", "Documents", "Clothing", "Accessories",
              "Bags", "Books/Stationery", "Keys", "ID Cards", "Other"]

STATUS_OPTIONS = ["All", "Unclaimed", "Possible Match", "Claimed", "Archived"]

# ---------------------------------------------------------------------------
# DEEP-LINK: ?item_id=X  — set by QR codes on storage tags
# ---------------------------------------------------------------------------
_qp = st.query_params
_deep_item_id = _qp.get("item_id", None)
if _deep_item_id:
    try:
        _deep_item_id = int(_deep_item_id)
    except (ValueError, TypeError):
        _deep_item_id = None

# ---------------------------------------------------------------------------
# SESSION STATE DEFAULTS
# ---------------------------------------------------------------------------
if "role" not in st.session_state:
    st.session_state.role = None          # None | "student" | "admin"
if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# ---------------------------------------------------------------------------
# HELPER: global logout
# ---------------------------------------------------------------------------
def do_logout():
    st.session_state.role = None
    st.session_state.admin_logged_in = False
    auth.logout_student()


# ---------------------------------------------------------------------------
# DEEP-LINK HANDLER (runs before any login gate — anyone with the URL can view)
# ---------------------------------------------------------------------------
ui_helpers.apply_custom_theme("default")

if _deep_item_id:
    deep_item = db.get_item_by_id(_deep_item_id)
    if deep_item:
        st.title(f"📦 Item #{deep_item['item_id']} — {deep_item['item_name']}")
        type_icon = "🔴" if deep_item["type"] == "lost" else "🟢"
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Type:** {type_icon} {deep_item['type'].title()}")
        c2.markdown(f"**Category:** {deep_item['category']}")
        c3.markdown(ui_helpers.status_badge_html(deep_item["status"]), unsafe_allow_html=True)
        st.markdown("---")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown(f"**Description:** {deep_item['description'] or '—'}")
            st.markdown(f"**Date Lost/Found:** {deep_item['date_lost_found'] or '—'}")
            st.markdown(f"**Location:** {deep_item['location'] or '—'}")
        with col_r:
            st.markdown(f"**Storage Location:** {deep_item['storage_location'] or '—'}")
            st.markdown(f"**Reported by:** {deep_item['reporter_name'] or '—'}")
            st.markdown(f"**Contact:** {deep_item['contact'] or '—'}")
        if deep_item["image_paths"]:
            st.markdown("**Photos:**")
            ui_helpers.display_image_carousel(deep_item["image_paths"], f"deep_{deep_item['item_id']}")
        st.markdown("---")
        if st.button("✖ Close and go to Home"):
            st.query_params.clear()
            st.rerun()
        st.stop()
    else:
        st.warning(f"Item #{_deep_item_id} not found. It may have been removed.")
        if st.button("Go to Home"):
            st.query_params.clear()
            st.rerun()
        st.stop()


# ===========================================================================
# STEP 1 — ROLE SELECTION SCREEN
# Shown when no role has been chosen yet (fresh visit / after logout).
# ===========================================================================
if st.session_state.role is None:
    ui_helpers.apply_custom_theme("home")
    st.title("🔎 SmartMatch Trace")
    st.subheader("Welcome! Please choose how you'd like to sign in.")

    kpis = analytics.get_summary_kpis()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Reports",        kpis["total_items"])
    c2.metric("Recovery Rate",        f"{kpis['recovery_rate']}%")
    c3.metric("Avg. Recovery Time",   f"{kpis['avg_recovery_days']} days")
    c4.metric("Most Common Category", kpis["top_category"])

    st.markdown("---")

    col_s, col_a = st.columns(2)

    # ── Student card ────────────────────────────────────────────────────
    with col_s:
        with st.container(border=True):
            st.markdown("### 🎓 Student")
            st.caption("Report lost/found items, search, get matched, and file claims.")
            tab_login, tab_register = st.tabs(["Log In", "Create Account"])

            with tab_login:
                with st.form("student_login_form"):
                    s_email    = st.text_input("Email",    key="sl_email")
                    s_password = st.text_input("Password", key="sl_pass", type="password")
                    if st.form_submit_button("Log In as Student", use_container_width=True):
                        with st.spinner("Logging in..."):
                            ok, msg = auth.login_student(s_email, s_password)
                        if ok:
                            st.session_state.role = "student"
                            st.rerun()
                        else:
                            st.error(msg)

            with tab_register:
                with st.form("student_register_form"):
                    r_name     = st.text_input("Full Name",       key="sr_name")
                    r_email    = st.text_input("Email",           key="sr_email")
                    r_contact  = st.text_input("Contact Number",  key="sr_contact")
                    r_password = st.text_input("Password",        key="sr_pass", type="password")
                    if st.form_submit_button("Create Account", use_container_width=True):
                        with st.spinner("Creating account..."):
                            ok, msg = auth.register_student(r_name, r_email, r_contact, r_password)
                        if ok:
                            st.success(msg + " Please log in above.")
                        else:
                            st.error(msg)

    # ── Admin card ──────────────────────────────────────────────────────
    with col_a:
        with st.container(border=True):
            st.markdown("### 🔐 Admin / Staff")
            st.caption("Approve claims, manage records, view analytics and the admin panel.")
            with st.form("admin_login_form"):
                a_user = st.text_input("Username", key="al_user")
                a_pass = st.text_input("Password", key="al_pass", type="password")
                if st.form_submit_button("Log In as Admin", use_container_width=True):
                    with st.spinner("Checking credentials..."):
                        valid = (a_user == ui_helpers.ADMIN_USERNAME and
                                 a_pass == ui_helpers.ADMIN_PASSWORD)
                    if valid:
                        st.session_state.admin_logged_in = True
                        st.session_state.role = "admin"
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")

    st.stop()   # don't render anything else until a role is chosen


# ===========================================================================
# STEP 2 — ROLE IS CHOSEN: build sidebar navigation
# ===========================================================================

# ── Sidebar header ──────────────────────────────────────────────────────────
st.sidebar.title("🔎 SmartMatch Trace")

if st.session_state.role == "student":
    student = auth.current_student()
    st.sidebar.success(f"👋 Hi, {student['name']}")
    ui_helpers.render_notification_bell(student["user_id"])

    STUDENT_PAGES = [
        "Home", "Dashboard", "Analytics",
        "Report Lost Item", "Report Found Item",
        "Search & Filter", "Possible Matches", "Claims",
        "User Guidance",
    ]
    page = st.sidebar.radio("Navigate", STUDENT_PAGES)

    st.sidebar.markdown("---")
    if st.sidebar.button("Log out", key="student_logout_sidebar"):
        do_logout()
        st.rerun()

else:  # admin
    st.sidebar.info("👤 Logged in as Admin")

    ADMIN_PAGES = [
        "Home", "Dashboard", "Analytics",
        "Manage Claims", "Admin Panel",
        "User Guidance",
    ]
    page = st.sidebar.radio("Navigate", ADMIN_PAGES)

    st.sidebar.markdown("---")
    if st.sidebar.button("Log out", key="admin_logout_sidebar"):
        do_logout()
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("SmartMatch Trace\nSQLite • Pandas • NumPy • Matplotlib • Streamlit")

# Apply per-page theme
PAGE_THEME = {
    "Home":              "home",
    "Dashboard":         "dashboard",
    "Analytics":         "analytics",
    "Report Lost Item":  "report",
    "Report Found Item": "report",
    "Search & Filter":   "default",
    "Possible Matches":  "default",
    "Claims":            "default",
    "Manage Claims":     "login",
    "Admin Panel":       "login",
    "User Guidance":     "default",
}
ui_helpers.apply_custom_theme(PAGE_THEME.get(page, "default"))


# ===========================================================================
# PAGE: HOME  (both roles)
# ===========================================================================
if page == "Home":
    st.title("🔎 SmartMatch Trace")
    st.subheader("Helping our campus reunite people with what they've lost.")

    st.markdown("""
    Welcome! This system helps students and staff:
    - 📢 **Report** a lost or found item in seconds
    - 🔍 **Search** existing reports with filters
    - 🤝 **Get matched** automatically using category, location, date and description
    - ✅ **Verify ownership** before any item is released
    - 🔔 **Get notified** the moment something changes
    """)

    kpis = analytics.get_summary_kpis()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Reports",        kpis["total_items"])
    c2.metric("Recovery Rate",        f"{kpis['recovery_rate']}%")
    c3.metric("Avg. Recovery Time",   f"{kpis['avg_recovery_days']} days")
    c4.metric("Most Common Category", kpis["top_category"])

    st.markdown("---")
    if st.session_state.role == "student":
        st.success(f"Logged in as **{auth.current_student()['name']}** — use the sidebar to get started.")
    else:
        st.success("Logged in as **Admin** — use the sidebar to manage claims or the admin panel.")

    st.caption("Use the sidebar to navigate.")


# ===========================================================================
# PAGE: DASHBOARD  (both roles)
# ===========================================================================
elif page == "Dashboard":
    st.title("Dashboard")
    st.caption("Overview of all lost & found activity")

    with st.spinner("Loading dashboard..."):
        kpis = analytics.get_summary_kpis()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Items",    kpis["total_items"])
    col2.metric("Lost Reports",   kpis["lost_count"])
    col3.metric("Found Reports",  kpis["found_count"])
    col4.metric("Claimed",        kpis["claimed_count"])

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Unclaimed",          kpis["unclaimed_count"])
    col6.metric("Recovery Rate",      f"{kpis['recovery_rate']}%")
    col7.metric("Avg. Recovery Time", f"{kpis['avg_recovery_days']} days")
    col8.metric("Most Common Category", kpis["top_category"])

    st.markdown("---")
    st.subheader("Recent Reports")
    items = db.get_all_items()
    if items:
        for item in items[:8]:
            with st.container(border=True):
                ui_helpers.render_item_card_header(item)
                with st.expander("View Details"):
                    st.write(f"**Category:** {item['category']}  ·  **Date:** {item['date_lost_found']}")
                    st.write(f"**Description:** {item['description'] or '—'}")
                    if item["image_paths"]:
                        ui_helpers.display_image_carousel(item["image_paths"], item["item_id"])
    else:
        st.info("No items reported yet.")

    st.markdown("---")
    with st.spinner("Building charts..."):
        col_a, col_b = st.columns(2)
        with col_a:
            fig = charts.bar_items_by_category(analytics.items_by_category())
            ui_helpers.render_chart_with_insight(fig, chart_insights.category_insight(analytics.items_by_category()))
        with col_b:
            fig = charts.pie_claimed_vs_unclaimed(analytics.claimed_vs_unclaimed_count())
            ui_helpers.render_chart_with_insight(fig, chart_insights.status_insight(analytics.claimed_vs_unclaimed_count()))


# ===========================================================================
# PAGE: ANALYTICS  (both roles)
# ===========================================================================
elif page == "Analytics":
    st.title("Analytics & Insights")
    st.caption("Pandas + NumPy calculations, visualized with Matplotlib. Hover over any chart for a quick insight.")

    with st.spinner("Crunching the numbers..."):
        kpis = analytics.get_summary_kpis()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Recovery Rate",      f"{kpis['recovery_rate']}%")
    k2.metric("Avg. Recovery Time", f"{kpis['avg_recovery_days']} days")
    k3.metric("Top Category",       kpis["top_category"])
    k4.metric("Top Location",       kpis["top_location"])

    st.markdown("---")

    with st.spinner("Building charts..."):
        cat_series      = analytics.items_by_category()
        status_series   = analytics.claimed_vs_unclaimed_count()
        monthly_series  = analytics.monthly_trend()
        location_series = analytics.items_by_location()
        recovery_series = analytics.category_recovery_rate()
        hotspot_series  = analytics.location_hotspots()
        heatmap_df      = analytics.location_category_heatmap_data()

        row1_c1, row1_c2 = st.columns(2)
        with row1_c1:
            ui_helpers.render_chart_with_insight(
                charts.bar_items_by_category(cat_series),
                chart_insights.category_insight(cat_series))
        with row1_c2:
            ui_helpers.render_chart_with_insight(
                charts.pie_claimed_vs_unclaimed(status_series),
                chart_insights.status_insight(status_series))

        row2_c1, row2_c2 = st.columns(2)
        with row2_c1:
            ui_helpers.render_chart_with_insight(
                charts.line_monthly_trend(monthly_series),
                chart_insights.monthly_trend_insight(monthly_series))
        with row2_c2:
            ui_helpers.render_chart_with_insight(
                charts.bar_by_location(location_series),
                chart_insights.location_insight(location_series))

        row3_c1, row3_c2 = st.columns(2)
        with row3_c1:
            ui_helpers.render_chart_with_insight(
                charts.bar_category_recovery_rate(recovery_series),
                chart_insights.recovery_rate_insight(recovery_series))
        with row3_c2:
            ui_helpers.render_chart_with_insight(
                charts.bar_location_hotspots(hotspot_series),
                chart_insights.hotspot_insight(hotspot_series))

        # ── Day / Time pattern analysis ───────────────────────────────────
        st.markdown("---")
        st.subheader("Day & Time Pattern Analysis")
        st.caption(
            "When do items get reported most? A simple pandas groupby on "
            "`date_lost_found` (day-of-week) and `time_lost_found` (hour-of-day) — "
            "useful for deciding when to staff the lost & found desk.")

        day_series  = analytics.items_by_day_of_week()
        hour_series = analytics.items_by_hour_of_day()

        dt_col1, dt_col2 = st.columns(2)
        with dt_col1:
            ui_helpers.render_chart_with_insight(
                charts.bar_day_of_week(day_series),
                chart_insights.day_of_week_insight(day_series))
        with dt_col2:
            ui_helpers.render_chart_with_insight(
                charts.bar_hour_of_day(hour_series),
                chart_insights.hour_of_day_insight(hour_series))
        # ─────────────────────────────────────────────────────────────────

        st.markdown("---")
        st.subheader("Location vs Category Heatmap")
        ui_helpers.render_chart_with_insight(
            charts.heatmap_location_category(heatmap_df),
            chart_insights.heatmap_insight(heatmap_df),
            width_pct=70)

        st.markdown("---")
        st.subheader("Predict Likely Location")
        st.caption(
            "Frequency-based conditional probability from historical records — "
            "shows where items of a given category have historically been lost or found.")

        pred_col1, pred_col2 = st.columns(2)
        pred_category = pred_col1.selectbox("Category", CATEGORIES,  key="pred_category")
        pred_type     = pred_col2.selectbox("Item Type", ["lost", "found"], key="pred_type")

        pred_series  = analytics.predict_likely_location(pred_category, pred_type)
        pred_insight = chart_insights.location_prediction_insight(pred_category, pred_series)

        if pred_series.empty:
            st.info(pred_insight)
        else:
            ui_helpers.render_chart_with_insight(
                charts.bar_location_prediction(pred_series, pred_category),
                pred_insight)


# ===========================================================================
# PAGE: REPORT LOST ITEM  (student only)
# ===========================================================================
elif page == "Report Lost Item":
    student = auth.current_student()
    st.title("Report a Lost Item")
    st.caption("Fill in as much detail as possible — it improves match accuracy.")

    with st.form("lost_item_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        item_name = c1.text_input("Item Name*", placeholder="e.g. Blue Water Bottle")
        category  = c2.selectbox("Category*", CATEGORIES)

        _pred = analytics.predict_likely_location(category, item_type="lost")
        if not _pred.empty:
            st.info(
                f"📍 Most likely location for **{category}** lost items: "
                f"**{_pred.index[0]}** ({_pred.iloc[0]:.1f}% historical probability)")

        description = st.text_area(
            "Description / Identifying Features*",
            placeholder="Color, brand, stickers, scratches, contents, etc.")

        c3, c4, c5 = st.columns(3)
        date_lost = c3.date_input("Date Lost*", value=date.today())
        time_lost = c4.time_input("Approx. Time Lost")
        location  = c5.text_input("Location Lost*", placeholder="e.g. Library, Canteen")

        c6, c7 = st.columns(2)
        reporter_name = c6.text_input("Your Name*",            value=student["name"])
        contact       = c7.text_input("Contact (phone/email)*", value=student["contact"] or "")

        uploaded_images = st.file_uploader(
            "Photos of the item (optional, helps with matching)",
            type=["png", "jpg", "jpeg"], accept_multiple_files=True)

        submitted = st.form_submit_button("Submit Lost Report", width="stretch")

        if submitted:
            if not item_name or not category or not location or not reporter_name or not contact:
                st.error("Please fill in all required (*) fields.")
            else:
                with st.spinner("Saving your report..."):
                    image_paths = ui_helpers.save_uploaded_images(uploaded_images)
                    new_id = db.add_item(
                        item_name=item_name, type_="lost", category=category,
                        description=description, date_lost_found=str(date_lost),
                        time_lost_found=str(time_lost), location=location,
                        storage_location=None, reporter_name=reporter_name, contact=contact,
                        image_paths=image_paths, user_id=student["user_id"])
                    matches = match_engine.find_matches_for_lost_item(new_id)

                st.success(f"Lost item reported successfully! Reference ID: #{new_id}")
                st.balloons()
                if matches:
                    st.info(f"Good news — {len(matches)} possible match(es) already found! "
                            "Check the 'Possible Matches' page.")


# ===========================================================================
# PAGE: REPORT FOUND ITEM  (student only)
# ===========================================================================
elif page == "Report Found Item":
    student = auth.current_student()
    st.title("Report a Found Item")
    st.caption("Thank you for helping return this item to its owner.")

    with st.form("found_item_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        item_name = c1.text_input("Item Name*", placeholder="e.g. Black Umbrella")
        category  = c2.selectbox("Category*", CATEGORIES)

        description = st.text_area(
            "Description*", placeholder="Color, brand, condition, any identifying marks")

        c3, c4, c5 = st.columns(3)
        date_found = c3.date_input("Date Found*", value=date.today())
        time_found = c4.time_input("Approx. Time Found")
        location   = c5.text_input("Location Found*", placeholder="e.g. Auditorium")

        storage_location = st.text_input(
            "Current Storage Location*", placeholder="e.g. Admin Office, Security Desk")

        c6, c7 = st.columns(2)
        finder_name = c6.text_input("Your Name*",             value=student["name"])
        contact     = c7.text_input("Contact (phone/email)*", value=student["contact"] or "")

        uploaded_images = st.file_uploader(
            "Photos of the item (recommended — helps the real owner recognize it)",
            type=["png", "jpg", "jpeg"], accept_multiple_files=True)

        submitted = st.form_submit_button("Submit Found Report", width="stretch")

        if submitted:
            if not item_name or not category or not location or not storage_location \
                    or not finder_name or not contact:
                st.error("Please fill in all required (*) fields.")
            else:
                with st.spinner("Saving your report..."):
                    image_paths = ui_helpers.save_uploaded_images(uploaded_images)
                    new_id = db.add_item(
                        item_name=item_name, type_="found", category=category,
                        description=description, date_lost_found=str(date_found),
                        time_lost_found=str(time_found), location=location,
                        storage_location=storage_location, reporter_name=finder_name, contact=contact,
                        image_paths=image_paths, user_id=student["user_id"])

                    reverse_matches = match_engine.find_matches_for_found_item(new_id)
                    notified = 0
                    for m in reverse_matches:
                        lost_owner_id = m["lost_item"]["user_id"]
                        if lost_owner_id:
                            db.add_notification(
                                lost_owner_id,
                                "A possible match was found for your lost item.",
                                icon="🔔", item_id=m["lost_item"]["item_id"])
                            notified += 1

                st.session_state["found_report_new_id"]     = new_id
                st.session_state["found_report_notified"]   = notified

    if st.session_state.get("found_report_new_id"):
        _new_id   = st.session_state["found_report_new_id"]
        _notified = st.session_state.get("found_report_notified", 0)

        st.success(f"Found item reported successfully! Reference ID: #{_new_id}")
        st.balloons()

        _base_url = qr_code.get_base_url()
        _tag_pdf  = qr_code.generate_storage_tag_pdf(db.get_item_by_id(_new_id), _base_url)
        st.download_button(
            label="🏷️ Download Storage Tag (QR PDF)",
            data=_tag_pdf,
            file_name=f"storage_tag_item_{_new_id}.pdf",
            mime="application/pdf",
            help="Print and attach to the item or its bag.")

        if _notified:
            st.info(f"{_notified} student(s) with a matching lost report have been notified.")

        del st.session_state["found_report_new_id"]
        del st.session_state["found_report_notified"]


# ===========================================================================
# PAGE: SEARCH & FILTER  (student only)
# ===========================================================================
elif page == "Search & Filter":
    student = auth.current_student()
    st.title("Search & Filter Items")

    c1, c2, c3, c4 = st.columns(4)
    keyword   = c1.text_input("Keyword", placeholder="Search name/description")
    category  = c2.selectbox("Category", ["All"] + CATEGORIES)
    status    = c3.selectbox("Status",   STATUS_OPTIONS)
    item_type = c4.selectbox("Type",     ["All", "lost", "found"])

    c5, c6, c7 = st.columns(3)
    location  = c5.text_input("Location contains")
    date_from = c6.date_input("From date", value=None)
    date_to   = c7.date_input("To date",   value=None)

    only_mine = st.checkbox("Only show my own reports")

    with st.spinner("Searching..."):
        results = db.search_items(
            keyword=keyword or None,
            category=category,
            status=status,
            item_type=item_type,
            location=location or None,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to)   if date_to   else None)
        if only_mine:
            results = [r for r in results if r["user_id"] == student["user_id"]]

    st.markdown(f"**{len(results)} result(s) found**")

    if results:
        for item in results:
            with st.container(border=True):
                ui_helpers.render_item_card_header(item)
                with st.expander("View Details"):
                    st.write(f"**Category:** {item['category']}  ·  **Date:** {item['date_lost_found']}")
                    st.write(f"**Description:** {item['description'] or '—'}")
                    st.write(f"**Reported by:** {item['reporter_name'] or '—'}")
                    if item["image_paths"]:
                        ui_helpers.display_image_carousel(item["image_paths"], item["item_id"])

        df  = pd.DataFrame([dict(r) for r in results]).drop(columns=["image_paths"], errors="ignore")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Export Results to CSV", data=csv,
                           file_name="lost_found_search_results.csv", mime="text/csv")
    else:
        st.info("No items match your filters.")


# ===========================================================================
# PAGE: POSSIBLE MATCHES  (student only)
# ===========================================================================
elif page == "Possible Matches":
    student = auth.current_student()
    st.title("Possible Matches")
    st.caption("Compares your open lost reports against found reports using category, "
               "location, date proximity and description keyword overlap.")

    min_score = st.slider("Minimum match score to show", 0, 100, 25, step=5)

    with st.spinner("Comparing your lost reports against found reports..."):
        all_items     = db.get_all_items()
        my_lost_items = [i for i in all_items
                         if i["type"] == "lost" and i["user_id"] == student["user_id"]
                         and i["status"] != "Claimed"]

        my_matches = []
        for lost in my_lost_items:
            matches = match_engine.find_matches_for_lost_item(lost["item_id"], min_score=min_score)
            if matches:
                my_matches.append({"lost_item": lost, "matches": matches})

    if not my_matches:
        st.info("No possible matches found for your lost reports at this score threshold.")
    else:
        for entry in my_matches:
            lost = entry["lost_item"]
            with st.expander(
                f"Lost: #{lost['item_id']} — {lost['item_name']} "
                f"({lost['category']}, reported {lost['date_lost_found']})"):

                st.write(f"**Description:** {lost['description'] or '—'}")
                st.write(f"**Location lost:** {lost['location'] or '—'}")
                if lost["image_paths"]:
                    ui_helpers.display_image_carousel(
                        lost["image_paths"], f"lost_{lost['item_id']}", caption="Your lost item photo")

                for match in entry["matches"]:
                    found = match["found_item"]
                    st.markdown(f"---\n**Candidate match:** #{found['item_id']} — "
                                f"{found['item_name']} · Score: **{match['score']}/100**")
                    bd = match["breakdown"]
                    st.write(
                        f"Category: {bd['category_score']}/35 · "
                        f"Location: {bd['location_score']}/25 · "
                        f"Date: {bd['date_score']}/20 · "
                        f"Keywords: {bd['keyword_score']}/20")
                    st.write(f"Found at **{found['location']}**, stored at "
                             f"**{found['storage_location'] or 'not specified'}**")
                    if found["image_paths"]:
                        ui_helpers.display_image_carousel(
                            found["image_paths"], f"found_{found['item_id']}", caption="Found item photo")

                    if st.button(f"File Claim for Item #{found['item_id']}",
                                 key=f"claim_{lost['item_id']}_{found['item_id']}"):
                        with st.spinner("Filing claim..."):
                            new_claim_id = db.add_claim(
                                found["item_id"], student["name"],
                                verification_notes=f"Auto-suggested match (score {match['score']})",
                                verification_answer=lost["description"] or "",
                                user_id=student["user_id"])

                        if new_claim_id is None:
                            st.error("This item is no longer available to claim — "
                                     "it may have already been claimed by someone else.")
                        else:
                            st.success("Claim filed. Go to the Claims page to track verification.")
                            new_claim = db.get_claims_for_user(student["user_id"])
                            new_claim = next((c for c in new_claim if c["claim_id"] == new_claim_id), None)
                            if new_claim:
                                pdf_bytes = claim_receipt.generate_claim_receipt_pdf(new_claim, found)
                                st.download_button(
                                    label="📄 Download Claim Receipt (PDF)",
                                    data=pdf_bytes,
                                    file_name=f"claim_receipt_{new_claim_id}.pdf",
                                    mime="application/pdf",
                                    key=f"receipt_match_{new_claim_id}",
                                    help="Show this at the admin desk when collecting your item.")
                            st.balloons()
                            st.rerun()


# ===========================================================================
# PAGE: CLAIMS  (student only — file a claim)
# ===========================================================================
elif page == "Claims":
    student = auth.current_student()
    st.title("File a Claim")
    st.caption("Select an unclaimed found item, describe an identifying detail, and submit your claim. "
               "An admin will verify and approve it.")

    found_items = [i for i in db.get_all_items()
                   if i["type"] == "found" and i["status"] in ("Unclaimed", "Possible Match")]

    if not found_items:
        st.info("No unclaimed found items available to claim right now.")
    else:
        options = {f"#{i['item_id']} — {i['item_name']} ({i['category']})": i["item_id"]
                   for i in found_items}
        choice = st.selectbox("Select Found Item", list(options.keys()))

        selected_item = db.get_item_by_id(options[choice])
        if selected_item and selected_item["image_paths"]:
            st.caption("Photo of this item (for reference):")
            ui_helpers.display_image_carousel(selected_item["image_paths"], "claim_preview")

        notes = st.text_area("Notes (any extra context, optional)")

        st.markdown("**Owner Verification**")
        st.caption("Describe a specific identifying detail (a mark, sticker, contents, scratch, etc.) "
                   "that wouldn't be obvious just from looking at it. "
                   "An admin will compare this against the original found-item description before approving.")
        verification_answer = st.text_area(
            "Describe a specific identifying detail*",
            placeholder="e.g. There's a small crack on the back-left corner, and a blue keychain attached to the zipper.")

        if st.button("Submit Claim"):
            if not verification_answer:
                st.error("Please describe an identifying detail for owner verification.")
            else:
                with st.spinner("Submitting claim..."):
                    new_claim_id = db.add_claim(options[choice], student["name"], notes,
                                                verification_answer, user_id=student["user_id"])

                if new_claim_id is None:
                    st.error("This item is no longer available to claim — it may have already been claimed.")
                else:
                    st.success("Claim submitted and pending verification.")
                    st.balloons()

                    new_claim = db.get_claims_for_user(student["user_id"])
                    new_claim = next((c for c in new_claim if c["claim_id"] == new_claim_id), None)
                    if new_claim and selected_item:
                        pdf_bytes = claim_receipt.generate_claim_receipt_pdf(new_claim, selected_item)
                        st.download_button(
                            label="📄 Download Claim Receipt (PDF)",
                            data=pdf_bytes,
                            file_name=f"claim_receipt_{new_claim_id}.pdf",
                            mime="application/pdf",
                            help="Show this at the admin desk when collecting your item.")

                    st.rerun()


# ===========================================================================
# PAGE: MANAGE CLAIMS  (admin only)
# ===========================================================================
elif page == "Manage Claims":
    st.title("Manage Claims")
    st.caption("Review, approve, or reject student claims.")

    with st.spinner("Loading claims..."):
        claims = db.get_all_claims()

    if not claims:
        st.info("No claims filed yet.")
    else:
        for c in claims:
            with st.container(border=True):
                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    st.write(f"**Claim #{c['claim_id']}** — Item: {c['item_name']} "
                             f"({c['category']}) · Claimant: {c['claimant_name']}")
                    st.caption(f"Filed on {c['claim_date']}")

                    item = db.get_item_by_id(c["item_id"])
                    st.write(f"**Original item description:** {item['description'] or '—'}")
                    st.write(f"**Claimant's verification answer:** {c['verification_answer'] or '—'}")
                    if c["verification_notes"]:
                        st.caption(f"Extra notes: {c['verification_notes']}")
                with cc2:
                    ui_helpers.render_status_badge(c["verified"])

                if c["verified"] == "Pending":
                    b1, b2 = st.columns(2)
                    if b1.button("Verify & Approve", key=f"verify_{c['claim_id']}"):
                        with st.spinner("Updating..."):
                            db.update_claim_status(c["claim_id"], c["item_id"], "Verified")
                        st.session_state["just_verified_claim_id"] = c["claim_id"]
                        st.balloons()
                        st.rerun()
                    if b2.button("Reject", key=f"reject_{c['claim_id']}"):
                        with st.spinner("Updating..."):
                            db.update_claim_status(c["claim_id"], c["item_id"], "Rejected")
                        st.rerun()

                # Receipt only shown immediately after approving in this session
                if (c["verified"] == "Verified" and
                        st.session_state.get("just_verified_claim_id") == c["claim_id"]):
                    receipt_item = db.get_item_by_id(c["item_id"])
                    if receipt_item:
                        pdf_bytes = claim_receipt.generate_claim_receipt_pdf(c, receipt_item)
                        st.download_button(
                            label=f"📄 Receipt for Claim #{c['claim_id']}",
                            data=pdf_bytes,
                            file_name=f"claim_receipt_{c['claim_id']}.pdf",
                            mime="application/pdf",
                            key=f"receipt_admin_{c['claim_id']}",
                            help="Print and give to the student for item collection.")


# ===========================================================================
# PAGE: ADMIN PANEL  (admin only)
# ===========================================================================
elif page == "Admin Panel":
    st.title("Admin Panel")
    st.caption("Manage records directly — update status, archive, or delete.")

    with st.spinner("Loading records..."):
        items = db.get_all_items()

    if not items:
        st.info("No items in the system yet.")
    else:
        df = pd.DataFrame([dict(r) for r in items])
        st.dataframe(df.drop(columns=["image_paths"], errors="ignore"),
                     width="stretch", hide_index=True)

        st.markdown("---")
        st.subheader("Update / Archive / Delete an Item")

        options = {f"#{i['item_id']} — {i['item_name']}": i["item_id"] for i in items}
        choice   = st.selectbox("Select item", list(options.keys()))
        item_id  = options[choice]
        current_item = db.get_item_by_id(item_id)

        if current_item["image_paths"]:
            st.caption("Current photos:")
            ui_helpers.display_image_carousel(current_item["image_paths"], f"admin_{item_id}")

        st.subheader("✏️ Edit Record")
        with st.form(f"edit_item_form_{item_id}"):
            ea, eb = st.columns(2)
            e_name     = ea.text_input("Item Name", value=current_item["item_name"] or "")
            e_category = eb.selectbox("Category", CATEGORIES,
                             index=CATEGORIES.index(current_item["category"])
                             if current_item["category"] in CATEGORIES else 0)

            ec, ed = st.columns(2)
            type_opts   = ["lost", "found"]
            e_type      = ec.selectbox("Type", type_opts,
                             index=type_opts.index(current_item["type"])
                             if current_item["type"] in type_opts else 0)
            status_opts = ["Unclaimed", "Possible Match", "Claimed", "Archived"]
            e_status    = ed.selectbox("Status", status_opts,
                             index=status_opts.index(current_item["status"])
                             if current_item["status"] in status_opts else 0)

            e_description = st.text_area("Description", value=current_item["description"] or "")

            ef, eg, eh = st.columns(3)
            e_date     = ef.text_input("Date Lost/Found (YYYY-MM-DD)", value=current_item["date_lost_found"] or "")
            e_location = eg.text_input("Location",         value=current_item["location"] or "")
            e_storage  = eh.text_input("Storage Location", value=current_item["storage_location"] or "")

            ei, ej = st.columns(2)
            e_reporter = ei.text_input("Reporter Name", value=current_item["reporter_name"] or "")
            e_contact  = ej.text_input("Contact",       value=current_item["contact"] or "")

            e_images = st.file_uploader(
                "Add photos (appended to existing photos)",
                type=["png", "jpg", "jpeg"], accept_multiple_files=True,
                key=f"edit_upload_{item_id}")

            save_btn = st.form_submit_button("💾 Save All Changes", type="primary")

        if save_btn:
            existing_paths = current_item["image_paths"] or ""
            new_paths      = ui_helpers.save_uploaded_images(e_images) or ""
            if existing_paths and new_paths:
                merged_paths = existing_paths + "," + new_paths
            elif new_paths:
                merged_paths = new_paths
            else:
                merged_paths = existing_paths or None

            with st.spinner("Saving changes..."):
                db.update_item(
                    item_id,
                    item_name=e_name, category=e_category, type=e_type,
                    status=e_status, description=e_description,
                    date_lost_found=e_date, location=e_location,
                    storage_location=e_storage, reporter_name=e_reporter,
                    contact=e_contact, image_paths=merged_paths)
            st.success("Record updated successfully.")
            st.rerun()

        st.markdown("---")
        st.caption("Quick actions")
        da1, da2 = st.columns(2)
        with da1:
            if st.button("📦 Archive Item", key=f"arch_{item_id}"):
                db.archive_item(item_id)
                st.success("Item archived.")
                st.rerun()
        with da2:
            if st.button("🗑️ Delete Permanently", key=f"del_{item_id}", type="primary"):
                db.delete_item(item_id)
                st.success("Item deleted.")
                st.rerun()

        st.markdown("---")

        if current_item["type"] == "found":
            st.subheader("🏷️ Storage Tag")
            st.caption("Print and attach to the item or its storage bag.")
            _base_url = qr_code.get_base_url()
            _qr_png   = qr_code.generate_qr_png(item_id, _base_url)
            _tag_pdf  = qr_code.generate_storage_tag_pdf(current_item, _base_url)
            qr_col, btn_col = st.columns([1, 3])
            with qr_col:
                st.image(_qr_png, caption=f"Item #{item_id}", width=140)
            with btn_col:
                st.download_button(
                    label="🏷️ Download Storage Tag (PDF)",
                    data=_tag_pdf,
                    file_name=f"storage_tag_item_{item_id}.pdf",
                    mime="application/pdf",
                    key=f"admin_qr_tag_{item_id}")

        st.markdown("---")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Export All Records to CSV", data=csv,
                           file_name="all_lost_found_records.csv", mime="text/csv")


# ===========================================================================
# PAGE: USER GUIDANCE  (both roles)
# ===========================================================================
elif page == "User Guidance":
    st.title("How to Use This System")

    if st.session_state.role == "student":
        st.markdown("""
        ### If you lost something
        1. Go to **Report Lost Item** and fill in as much detail as possible.
        2. Check **Possible Matches** — the system automatically compares your report against found items.
        3. If a match looks right, click **File Claim** and answer the verification question.
        4. Watch the 🔔 notification bell in the sidebar for updates on your claim.

        ### If you found something
        1. Go to **Report Found Item** and note where you found it and where you've stored it.
        2. Hand the item in to the location you specified (e.g. Admin Office).
        3. If it matches an existing lost report, that student is notified automatically.

        ### Owner verification
        When filing a claim you'll describe a specific identifying detail about the item.
        An admin compares this against the original description before approving — this
        prevents someone from claiming an item that isn't theirs.

        ### Status badges
        🟡 Pending · 🔵 Possible Match / Under Verification · 🟢 Claimed/Verified ·
        🔴 Rejected · ⚪ Unclaimed
        """)
    else:
        st.markdown("""
        ### If you lost something
        1. Go to **Report Lost Item** and fill in as much detail as possible.
        2. Check **Possible Matches** — the system automatically compares your report against found items.
        3. If a match looks right, click **File Claim** and answer the verification question.
        4. Watch the 🔔 notification bell in the sidebar for updates on your claim.

        ### If you found something
        1. Go to **Report Found Item** and note where you found it and where you've stored it.
        2. Hand the item in to the location you specified (e.g. Admin Office).
        3. If it matches an existing lost report, that student is notified automatically.

        ### Owner verification
        When filing a claim you'll describe a specific identifying detail about the item.
        An admin compares this against the original description before approving — this
        prevents someone from claiming an item that isn't theirs.

        ### Status badges
        🟡 Pending · 🔵 Possible Match / Under Verification · 🟢 Claimed/Verified ·
        🔴 Rejected · ⚪ Unclaimed

        ### For administrators
        Use **Manage Claims** to approve or reject student claims.
        Use the **Admin Panel** to update statuses, archive resolved cases, or export records.
        Use **Analytics** to see trends.

        Admin demo credentials: username `admin`, password `admin123`
        (change these in `ui_helpers.py` before a real deployment).
        """)
