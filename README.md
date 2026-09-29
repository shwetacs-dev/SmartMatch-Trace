# Lost & Found Management System

A college-level Lost & Found Management System built with:
**SQLite + SQL + Pandas + NumPy + Matplotlib + Streamlit**

## Project Structure

```
lost_found_system/
├── app.py              # Main Streamlit app (all pages/navigation/UI)
├── database.py          # SQLite schema + all CRUD functions (SQL layer)
├── match_engine.py      # Rule-based "possible match" scoring engine
├── analytics.py         # Pandas/NumPy calculations (Data Science layer)
├── charts.py             # Matplotlib visualizations
├── seed_data.py           # Populates sample data for demo/testing
├── requirements.txt      # Python dependencies
└── lost_and_found.db     # SQLite database (auto-created on first run)
```

## How to Run

1. **Install dependencies** (only needs to be done once):
   ```
   pip install -r requirements.txt
   ```

2. **(Optional but recommended) Seed sample data** so the dashboard and
   charts have data to show immediately:
   ```
   python seed_data.py
   ```
   This clears any existing data and inserts realistic sample lost/found
   reports and claims. Skip this step if you want to start with a
   completely empty system and enter data manually.

3. **Run the app**:
   ```
   streamlit run app.py
   ```
   This opens the app in your browser automatically (usually at
   `http://localhost:8501`).

## Application Pages

| Page | Purpose |
|---|---|
| Dashboard | KPI cards + recent reports + quick charts |
| Report Lost Item | Form to log a lost item (supports photo uploads) |
| Report Found Item | Form to log a found item (supports photo uploads) |
| Search & Filter | Keyword + category/status/location/date filters, CSV export, photo gallery |
| Possible Matches | Rule-based matching between lost and found reports, with photos |
| Claims | File a claim (with owner verification question) + admin-only approval |
| Analytics | Full set of Pandas/NumPy/Matplotlib visualizations |
| Admin Panel | Admin-login-protected: update status, archive, delete, export records |
| User Guidance | Simple instructions for end users |

## New Features (v2)

- **Admin login** — Both the Admin Panel and claim approval (in Claims →
  "Manage Existing Claims") require a login. Default demo credentials:
  - Username: `admin`
  - Password: `admin123`

  Change these in `ui_helpers.py` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`)
  before any real deployment — they are intentionally simple for a
  college-level demo.

- **Multiple images per item** — Reporting a lost or found item now lets
  you attach one or more photos. They're stored in the `uploaded_images/`
  folder and shown wherever that item appears (search results, possible
  matches, admin panel).

- **Owner verification on claims** — When filing a claim, the claimant
  must describe a specific identifying detail about the item (not just
  their name). The admin sees this answer side-by-side with the original
  item description before approving or rejecting the claim.

- **Colourful animated theme** — A custom CSS theme (`ui_helpers.py` →
  `CUSTOM_CSS`) gives the app a soft animated gradient background,
  styled sidebar, hover effects on metric cards and buttons.

- **Loading spinners & success animations** — Searches, form submissions,
  match scoring, and chart generation now show a spinner while working,
  and successful submissions trigger a small balloon animation.

## How the Match Engine Works (for your report)

For every open "lost" report, the system compares it against every
"found" report still available and produces a score out of 100:

- **Category match** — 35 points if categories are identical
- **Location similarity** — up to 25 points (exact or partial text match)
- **Date proximity** — up to 20 points, decaying linearly over 30 days
- **Description keyword overlap** — up to 20 points, using Jaccard
  similarity between the significant words in both descriptions

This is intentionally rule-based (not machine learning) so the logic is
fully explainable in a viva/demo — a good fit for a first-year project.

## Database Schema

**items**
`item_id, item_name, type (lost/found), category, description,
date_reported, date_lost_found, time_lost_found, location,
storage_location, status, reporter_name, contact`

**claims**
`claim_id, item_id (FK), claimant_name, claim_date, verified,
verification_notes`

## Notes for Your Report

- The **Data Science layer** (`analytics.py`) pulls data out of SQLite with
  `pd.read_sql_query()`, then uses pandas groupby/value_counts and a NumPy
  mean calculation (for average recovery time) to generate every statistic
  shown on the Analytics page.
- All charts use **Matplotlib only** (bar, pie/donut, line, horizontal bar,
  and a custom heatmap built with `imshow` — no Seaborn).
- The recovery rate is calculated as: `Claimed found-items / Total found-items`.
- Average recovery time is the mean number of days between an item being
  found and its claim being verified.

## New Features (v3) -- Competition Polish

- **Student accounts** — students register/log in (name, email, contact,
  password) to report items, search, view their own possible matches,
  and file claims. Passwords are hashed (SHA-256) before storage.
  Admin login stays separate (see `ui_helpers.py`).

- **In-app notifications 🔔** — shown in the sidebar bell for the logged-in
  student:
  - "A possible match was found for your lost item" (fires when someone
    reports a *found* item that matches your open lost report)
  - "Your claim is under verification" (fires the moment you file a claim)
  - "Your item has been successfully verified" (fires when an admin
    approves your claim)

- **Colour-matched, animated backgrounds** — each page type gets its own
  themed background (lively on Home, calm on Login, professional/muted
  on Dashboard & Analytics so charts stay readable, subtle on Report
  pages), all built with pure CSS (`ui_helpers.py` → `BACKGROUND_THEMES`,
  `BASE_CSS`). A translucent "card" wrapper keeps all text readable
  regardless of what's moving behind it.

- **Hover insights on every chart** — hovering over any Analytics/Dashboard
  chart shows a native tooltip with a one-line, data-driven insight
  (see `chart_insights.py`). The same insight is also shown as a caption
  underneath, in case a hover isn't convenient (e.g. touchscreens).

- **Status badges** — colour-coded pill badges (🟡 Pending, 🔵 Possible
  Match/Under Verification, 🟢 Claimed/Verified, 🔴 Rejected, ⚪ Unclaimed)
  used throughout instead of plain text.

- **Expandable item cards** — Dashboard and Search & Filter now show a
  compact one-line summary per item (name, location, status badge) that
  expands into full details + photos, instead of dumping everything at
  once.

- **Image carousel** — items with multiple photos show one main image
  with a clickable thumbnail strip underneath instead of a static row.

## Updated File List

| File | Role |
|---|---|
| `app.py` | Main Streamlit app / page routing |
| `database.py` | SQLite schema (now includes `users` and `notifications`) + CRUD |
| `auth.py` | Student registration/login/session logic |
| `match_engine.py` | Rule-based possible-match scoring (both directions: lost→found and found→lost) |
| `analytics.py` | Pandas/NumPy calculations |
| `charts.py` | Matplotlib chart drawing (theme-matched colours) |
| `chart_insights.py` | Plain-language insight text per chart (for hover tooltips) |
| `ui_helpers.py` | Backgrounds, animations, badges, image carousel, notifications, admin login |
| `seed_data.py` | Sample data generator |
| `view_database.py` | Standalone script to print the raw database contents |
| `export_db_to_pdf.py` | Standalone script to export the database as a PDF report |
