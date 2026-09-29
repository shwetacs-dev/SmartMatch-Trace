"""
database.py
------------
Handles the SQLite database for the Lost & Found Management System.

Responsibilities:
  - Create the database and tables if they don't exist
  - Provide simple CRUD (Create, Read, Update, Delete) functions
  - Keep all raw SQL in ONE place so the rest of the app never writes SQL directly

Tables:
  users         -> student accounts (admin uses a separate hardcoded login)
  items         -> every lost or found report
  claims        -> claim requests linked to a found item
  notifications -> in-app alerts for students (matches, claim status changes)
"""

import sqlite3
import os
from datetime import datetime

DB_NAME = "lost_and_found.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)


def get_connection():
    """Return a new SQLite connection. Each function opens/closes its own
    connection so the app is safe to use with Streamlit's rerun model."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Create tables if they do not already exist. Safe to call every run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            contact TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('lost', 'found')),
            category TEXT NOT NULL,
            description TEXT,
            date_reported TEXT NOT NULL,
            date_lost_found TEXT,
            time_lost_found TEXT,
            location TEXT,
            storage_location TEXT,
            status TEXT NOT NULL DEFAULT 'Unclaimed'
                CHECK(status IN ('Unclaimed', 'Possible Match', 'Claimed', 'Archived')),
            reporter_name TEXT,
            contact TEXT,
            image_paths TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            claim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            claimant_name TEXT NOT NULL,
            claim_date TEXT NOT NULL,
            verified TEXT NOT NULL DEFAULT 'Pending'
                CHECK(verified IN ('Pending', 'Verified', 'Rejected')),
            verification_notes TEXT,
            verification_answer TEXT,
            user_id INTEGER,
            FOREIGN KEY (item_id) REFERENCES items(item_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT '🔔',
            item_id INTEGER,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (item_id) REFERENCES items(item_id)
        )
    """)

    # --- Lightweight migration for databases created before these columns existed ---
    existing_item_cols = [row["name"] for row in conn.execute("PRAGMA table_info(items)").fetchall()]
    if "image_paths" not in existing_item_cols:
        conn.execute("ALTER TABLE items ADD COLUMN image_paths TEXT")
    if "user_id" not in existing_item_cols:
        conn.execute("ALTER TABLE items ADD COLUMN user_id INTEGER")

    existing_claim_cols = [row["name"] for row in conn.execute("PRAGMA table_info(claims)").fetchall()]
    if "verification_answer" not in existing_claim_cols:
        conn.execute("ALTER TABLE claims ADD COLUMN verification_answer TEXT")
    if "user_id" not in existing_claim_cols:
        conn.execute("ALTER TABLE claims ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# ITEM CRUD
# ---------------------------------------------------------------------------

def add_item(item_name, type_, category, description, date_lost_found,
             time_lost_found, location, storage_location, reporter_name, contact,
             image_paths=None, user_id=None):
    """Insert a new lost or found item report. Returns the new item_id.
    image_paths: a comma-separated string of saved image filenames, or None.
    user_id: the logged-in student's account id, so items can be tied to "My Items"."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO items
        (item_name, type, category, description, date_reported, date_lost_found,
         time_lost_found, location, storage_location, status, reporter_name, contact,
         image_paths, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Unclaimed', ?, ?, ?, ?)
    """, (
        item_name, type_, category, description,
        datetime.now().strftime("%Y-%m-%d"),
        date_lost_found, time_lost_found, location,
        storage_location, reporter_name, contact, image_paths, user_id
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_items():
    """Return every item row as a list of sqlite3.Row objects."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM items ORDER BY item_id DESC").fetchall()
    conn.close()
    return rows


def get_item_by_id(item_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
    conn.close()
    return row


def search_items(keyword=None, category=None, status=None, item_type=None,
                  location=None, date_from=None, date_to=None):
    """Flexible search/filter. Any parameter left as None is ignored."""
    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if keyword:
        query += " AND (item_name LIKE ? OR description LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    if status and status != "All":
        query += " AND status = ?"
        params.append(status)
    if item_type and item_type != "All":
        query += " AND type = ?"
        params.append(item_type)
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if date_from:
        query += " AND date_lost_found >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date_lost_found <= ?"
        params.append(date_to)

    query += " ORDER BY item_id DESC"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def update_item_status(item_id, new_status):
    conn = get_connection()
    conn.execute("UPDATE items SET status = ? WHERE item_id = ?", (new_status, item_id))
    conn.commit()
    conn.close()


def update_item(item_id, **fields):
    """Generic update: update_item(5, location='Library', category='Electronics')"""
    if not fields:
        return
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [item_id]
    conn = get_connection()
    conn.execute(f"UPDATE items SET {set_clause} WHERE item_id = ?", values)
    conn.commit()
    conn.close()


def delete_item(item_id):
    """Permanently removes the item AND its claim history -- this is a real
    hard delete, used by Admin Panel's 'Delete Permanently' button.
    For a reversible alternative that keeps history intact for analytics,
    use archive_item() instead (sets status to 'Archived')."""
    conn = get_connection()
    conn.execute("DELETE FROM claims WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()


def archive_item(item_id):
    update_item_status(item_id, "Archived")


# ---------------------------------------------------------------------------
# CLAIMS CRUD
# ---------------------------------------------------------------------------

def add_claim(item_id, claimant_name, verification_notes="", verification_answer="", user_id=None):
    """verification_answer is the claimant's own description of an identifying
    feature of the item -- used by the admin to verify real ownership before
    releasing it (not shown back to the claimant).
    user_id: the logged-in student filing the claim (used for notifications).

    Returns the new claim_id, or None if the item can't be claimed right
    now (wrong item, not a 'found' item, or already Claimed/Archived) --
    guards against a claim silently reopening an item that's already
    been handed back to its owner."""
    item = get_item_by_id(item_id)
    if item is None or item["type"] != "found" or item["status"] in ("Claimed", "Archived"):
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claims (item_id, claimant_name, claim_date, verified, verification_notes,
                             verification_answer, user_id)
        VALUES (?, ?, ?, 'Pending', ?, ?, ?)
    """, (item_id, claimant_name, datetime.now().strftime("%Y-%m-%d"), verification_notes,
          verification_answer, user_id))
    conn.commit()
    claim_id = cur.lastrowid

    # Move the linked item into "Possible Match" until claim is verified
    conn.execute("UPDATE items SET status = 'Possible Match' WHERE item_id = ?", (item_id,))
    conn.commit()
    conn.close()

    if user_id:
        add_notification(user_id, "Your claim is under verification.", icon="🔵", item_id=item_id)

    return claim_id


def get_all_claims():
    conn = get_connection()
    rows = conn.execute("""
        SELECT claims.*, items.item_name, items.category, items.status AS item_status
        FROM claims
        JOIN items ON claims.item_id = items.item_id
        ORDER BY claims.claim_id DESC
    """).fetchall()
    conn.close()
    return rows


def update_claim_status(claim_id, item_id, decision, notes=""):
    """decision must be 'Verified' or 'Rejected'. Also creates the matching
    in-app notification for the student who filed the claim, if they were logged in."""
    conn = get_connection()
    claim = conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()

    conn.execute("""
        UPDATE claims SET verified = ?, verification_notes = ? WHERE claim_id = ?
    """, (decision, notes, claim_id))

    if decision == "Verified":
        conn.execute("UPDATE items SET status = 'Claimed' WHERE item_id = ?", (item_id,))
    elif decision == "Rejected":
        conn.execute("UPDATE items SET status = 'Unclaimed' WHERE item_id = ?", (item_id,))

    conn.commit()
    conn.close()

    if claim and claim["user_id"]:
        if decision == "Verified":
            add_notification(claim["user_id"],
                              "Your item has been successfully verified. You can collect it now!",
                              icon="✅", item_id=item_id)
        elif decision == "Rejected":
            add_notification(claim["user_id"],
                              "Your claim was not verified. Please contact the admin office for details.",
                              icon="🔴", item_id=item_id)


def get_categories():
    """Distinct categories currently in use, for dropdown filters."""
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT category FROM items ORDER BY category").fetchall()
    conn.close()
    return [r["category"] for r in rows]


def get_locations():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT location FROM items ORDER BY location").fetchall()
    conn.close()
    return [r["location"] for r in rows if r["location"]]


# ---------------------------------------------------------------------------
# USERS (student accounts)
# ---------------------------------------------------------------------------

def create_user(name, email, contact, password_hash):
    """Returns the new user_id, or None if the email is already registered."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (name, email, contact, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, contact, password_hash, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_items_for_user(user_id):
    """All lost/found items reported by this student -- used for 'My Items'."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM items WHERE user_id = ? ORDER BY item_id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_claims_for_user(user_id):
    """All claims filed by this student."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT claims.*, items.item_name, items.category
        FROM claims JOIN items ON claims.item_id = items.item_id
        WHERE claims.user_id = ?
        ORDER BY claims.claim_id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------------------------

def add_notification(user_id, message, icon="🔔", item_id=None):
    if not user_id:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notifications (user_id, message, icon, item_id, is_read, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
    """, (user_id, message, icon, item_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_notifications_for_user(user_id, limit=20):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM notifications WHERE user_id = ?
        ORDER BY notification_id DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return rows


def count_unread_notifications(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)
    ).fetchone()
    conn.close()
    return row["c"] if row else 0


def mark_all_notifications_read(user_id):
    conn = get_connection()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
