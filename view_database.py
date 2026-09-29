"""
view_database.py
------------------
A simple, standalone script that opens lost_and_found.db directly and
prints its contents to the terminal. This is what "opening the database
through code" actually looks like -- there's no separate app involved,
just Python reading the file.

Run with:
    python view_database.py
"""

import sqlite3

DB_PATH = "lost_and_found.db"


def view_table(cursor, table_name):
    print("=" * 70)
    print(f"TABLE: {table_name}")
    print("=" * 70)

    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    if not rows:
        print("(empty -- no rows in this table yet)\n")
        return

    # Print column headers
    col_names = [description[0] for description in cursor.description]
    print(" | ".join(col_names))
    print("-" * 70)

    # Print each row
    for row in rows:
        print(" | ".join(str(value) for value in row))

    print(f"\nTotal rows: {len(rows)}\n")


def main():
    # This one line is "opening the database through code"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # See what tables exist inside the .db file
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]

    print(f"\nOpened '{DB_PATH}' -- found {len(tables)} table(s): {tables}\n")

    for table in tables:
        view_table(cursor, table)

    conn.close()


if __name__ == "__main__":
    main()
