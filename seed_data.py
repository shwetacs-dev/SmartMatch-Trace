"""
seed_data.py
-------------
Populates the database with realistic sample data so the dashboard,
charts, and match engine all have something meaningful to show right away.

Run once with:
    python seed_data.py

Safe to re-run: it wipes and recreates the tables first.

Total records: 205 items (105 found + 100 lost) + ~40% claim rate.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

import database as db

random.seed(42)

CATEGORIES = ["Electronics", "Documents", "Clothing", "Accessories",
              "Bags", "Books/Stationery", "Keys", "ID Cards"]

LOCATIONS = [
    "Library", "Canteen", "Auditorium", "Main Gate", "Sports Ground",
    "Computer Lab", "Admin Office", "Hostel Block A", "Parking Area",
    "Lecture Hall 1", "Lecture Hall 2", "Science Block", "Arts Block",
    "Medical Centre", "Gym", "Cafeteria", "Seminar Hall", "Workshop Block",
    "Girls Hostel", "Boys Hostel",
]

# Realistic weighting: each category is MORE likely to be lost/found in a
# few plausible locations, with everywhere else still possible but rarer.
# Without this, location was picked with pure random.choice() over 20
# options -- every location ends up at roughly the same ~5%, so the
# "Predict Likely Location" chart had nothing real to detect. This gives
# the frequency model an actual pattern to surface, while still leaving
# some noise (it's not 100% deterministic).
CATEGORY_LOCATION_WEIGHTS = {
    "Electronics":       {"Computer Lab": 5, "Library": 3, "Canteen": 2},
    "Documents":         {"Admin Office": 5, "Library": 4, "Lecture Hall 1": 2},
    "Clothing":          {"Gym": 5, "Sports Ground": 4, "Hostel Block A": 2},
    "Accessories":       {"Canteen": 4, "Auditorium": 3, "Main Gate": 2},
    "Bags":              {"Lecture Hall 2": 4, "Library": 3, "Parking Area": 2},
    "Books/Stationery":  {"Library": 5, "Lecture Hall 1": 4, "Science Block": 2},
    "Keys":              {"Hostel Block A": 4, "Boys Hostel": 3, "Girls Hostel": 3},
    "ID Cards":          {"Main Gate": 4, "Admin Office": 3, "Canteen": 2},
}


def weighted_location(category):
    """Pick a location for this category: biased toward its 'likely spots'
    (see CATEGORY_LOCATION_WEIGHTS) most of the time, but still falls back
    to any location so the data doesn't look artificially perfect."""
    weights = CATEGORY_LOCATION_WEIGHTS.get(category, {})
    if weights and random.random() < 0.65:
        return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]
    return random.choice(LOCATIONS)

STORAGE_LOCATIONS = [
    "Admin Office", "Security Desk", "Library Counter",
    "Sports Office", "Hostel Warden Office",
]

ITEM_NAMES = {
    "Electronics": [
        "Wireless Earbuds", "Phone Charger", "Bluetooth Speaker",
        "USB Drive", "Calculator", "Laptop Charger", "Power Bank",
        "Smartwatch", "Earphones", "Portable Speaker",
    ],
    "Documents": [
        "Assignment Folder", "Lecture Notes", "Admit Card",
        "Certificate Copy", "Mark Sheet", "Hall Ticket",
        "Project Report", "Lab Manual", "Research Paper",
    ],
    "Clothing": [
        "Blue Jacket", "College Hoodie", "Sports Jersey",
        "Scarf", "Cap", "Raincoat", "Sweater", "Lab Coat",
        "Tracksuit Top", "Gloves",
    ],
    "Accessories": [
        "Wristwatch", "Sunglasses", "Hair Clip", "Wallet",
        "Belt", "Bracelet", "Ring", "Earrings", "Necklace", "Tie",
    ],
    "Bags": [
        "Black Backpack", "Laptop Bag", "Gym Bag", "Tote Bag",
        "Sling Bag", "Duffel Bag", "Drawstring Bag", "Handbag",
        "Document Bag", "Sports Kit Bag",
    ],
    "Books/Stationery": [
        "Physics Textbook", "Notebook Set", "Pen Case", "Sketchbook",
        "Chemistry Textbook", "Mathematics Textbook", "Graph Notebook",
        "Drawing Instruments", "Highlighter Set", "Geometry Box",
    ],
    "Keys": [
        "Bike Key", "Hostel Room Key", "Locker Key Set",
        "Car Key", "Cabinet Key", "Padlock Key",
    ],
    "ID Cards": [
        "College ID Card", "Library Card", "Bus Pass",
        "Canteen Card", "Gym Membership Card",
    ],
}

NAMES = [
    "Aarav", "Priya", "Rohan", "Sneha", "Karan", "Divya", "Arjun", "Meera",
    "Vikram", "Ananya", "Rahul", "Kavya", "Nikhil", "Pooja", "Sanjay",
    "Deepika", "Aditya", "Shreya", "Varun", "Nisha", "Harish", "Lakshmi",
    "Mohit", "Ritu", "Suresh", "Geeta", "Amit", "Sunita", "Rajesh", "Seema",
]

DESCRIPTIONS_FOUND = [
    "Found near the entrance, looks like it was left behind after class.",
    "Discovered on a bench, owner probably forgot it.",
    "Left on the floor near the exit, handed in immediately.",
    "Found on a table, appears to be in good condition.",
    "Spotted near the lockers, brought to admin for safekeeping.",
    "Left behind after an event, stored safely.",
    "Found during cleaning, kept for the owner to collect.",
    "Discovered on a chair, condition is fine.",
    "Left unattended for over an hour, taken in for safekeeping.",
    "Found near the notice board, owner please collect.",
]

DESCRIPTIONS_LOST = [
    "Lost sometime in the morning, please contact if found.",
    "Missing since yesterday, of high sentimental value.",
    "Lost during the event, would really appreciate if returned.",
    "Not sure exactly where I lost it, please check lost and found.",
    "Lost it somewhere on campus, would be very grateful for its return.",
    "Noticed it missing after class, please contact.",
    "Lost during the sports session, please return if found.",
    "Left it somewhere and can't remember where, please help.",
    "Missing since the afternoon, very important.",
    "Lost track of it during a busy day, please contact if found.",
]


def random_date(days_back_max=200):
    days_back = random.randint(0, days_back_max)
    return (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")


def wipe_tables():
    conn = db.get_connection()
    conn.execute("DELETE FROM notifications")
    conn.execute("DELETE FROM claims")
    conn.execute("DELETE FROM items")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('items', 'claims', 'notifications')")
    conn.commit()
    conn.close()


def seed():
    db.init_db()
    wipe_tables()

    item_ids_found = []

    # ── 105 found items ───────────────────────────────────────────────────
    for _ in range(105):
        category = random.choice(CATEGORIES)
        name = random.choice(ITEM_NAMES[category])
        location = weighted_location(category)
        date_found = random_date()
        item_id = db.add_item(
            item_name=name,
            type_="found",
            category=category,
            description=f"{name} — {random.choice(DESCRIPTIONS_FOUND)}",
            date_lost_found=date_found,
            time_lost_found=f"{random.randint(7, 20):02d}:{random.choice(['00','15','30','45'])}",
            location=location,
            storage_location=random.choice(STORAGE_LOCATIONS),
            reporter_name=random.choice(NAMES),
            contact=f"{random.randint(9000000000, 9999999999)}",
        )
        item_ids_found.append((item_id, category, date_found))

    # ── 100 lost items ────────────────────────────────────────────────────
    for _ in range(100):
        category = random.choice(CATEGORIES)
        name = random.choice(ITEM_NAMES[category])
        location = weighted_location(category)
        date_lost = random_date()
        db.add_item(
            item_name=name,
            type_="lost",
            category=category,
            description=f"{name} — {random.choice(DESCRIPTIONS_LOST)}",
            date_lost_found=date_lost,
            time_lost_found=f"{random.randint(7, 20):02d}:{random.choice(['00','15','30','45'])}",
            location=location,
            storage_location=None,
            reporter_name=random.choice(NAMES),
            contact=f"{random.randint(9000000000, 9999999999)}",
        )

    # ── Claims: ~40% of found items verified ──────────────────────────────
    to_claim = random.sample(item_ids_found, k=int(len(item_ids_found) * 0.4))
    for item_id, category, date_found in to_claim:
        claim_date = (
            datetime.strptime(date_found, "%Y-%m-%d") + timedelta(days=random.randint(1, 20))
        ).strftime("%Y-%m-%d")
        conn = db.get_connection()
        conn.execute("""
            INSERT INTO claims (item_id, claimant_name, claim_date, verified, verification_notes)
            VALUES (?, ?, ?, 'Verified', 'ID verified against description.')
        """, (item_id, random.choice(NAMES), claim_date))
        conn.execute("UPDATE items SET status = 'Claimed' WHERE item_id = ?", (item_id,))
        conn.commit()
        conn.close()

    print("Sample data seeded successfully:")
    print(f"  Found items : {len(item_ids_found)}")
    print(f"  Lost items  : 100")
    print(f"  Claims      : {len(to_claim)}")
    print(f"  Total items : {len(item_ids_found) + 100}")


if __name__ == "__main__":
    seed()
 