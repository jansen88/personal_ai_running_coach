# Run this to initialise SQLite database
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/strava.db')

def create_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # All individual runs
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
            pace_z5 REAL,
            run_type TEXT,
            is_race BOOLEAN,
            week_start TEXT
        )
    ''')

    # Summarise to weekly
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_summary (
            week_start TEXT,
            total_distance REAL,
            total_time REAL,
            time_easy REAL,
            time_z3 REAL,
            time_z4_or_5 REAL,
            avg_pace_base REAL,
            avg_pace_z3 REAL,
            avg_pace_z4_or_5 REAL,
            num_races INTEGER,
            race_summary TEXT,
            PRIMARY KEY (week_start)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database created at", DB_PATH)

if __name__ == "__main__":
    create_db()