# Run this to initialise SQLite database
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/strava.db')

# assumes data folder should already exist
# it should because i initialised it with a blank.json
# when I committed

def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            distance REAL,
            duration REAL,
            pace REAL,
            elevation_gain REAL,
            type TEXT,
            time_z1 REAL,
            time_z2 REAL,
            time_z3 REAL,
            time_z4 REAL,
            time_z5 REAL,
            pace_z1 REAL,
            pace_z2 REAL,
            pace_z3 REAL,
            pace_z4 REAL,
            pace_z5 REAL
        )
    ''')
    conn.commit()
    conn.close()
    print("Database created at", DB_PATH)

if __name__ == "__main__":
    create_db()