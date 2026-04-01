# Developer notes:
# - Assumes Strava API keys and OAuth set up (see README)
# - Scrapes last N activities (1 API call)
# - Then fetches streams per activity (N API calls)
# - Computes time in HR zones + pace per zone
# - Strava rate limits: 100 requests / 15 mins, 1000 daily

import requests
import sqlite3

from src.config import (
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_REFRESH_TOKEN,
    DB_PATH,
    MAX_HEART_RATE,
    ZONES,
    NUMBER_OF_RUNS_TO_FETCH
)


CLIENT_ID = STRAVA_CLIENT_ID
CLIENT_SECRET = STRAVA_CLIENT_SECRET
REFRESH_TOKEN = STRAVA_REFRESH_TOKEN


def get_access_token():
    url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()['access_token']


# fetch at ALL RUNS level
def fetch_activities(token, per_page):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f'Bearer {token}'}
    params = {'per_page': per_page}
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()

# fetch at ACTIVITY level (one level down)
def fetch_streams(token, activity_id):
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        "keys": "heartrate,time,distance",
        "key_by_type": "true"
    }

    res = requests.get(url, headers=headers, params=params)

    if res.status_code != 200:
        return None

    data = res.json()

    if "heartrate" not in data or "distance" not in data or "time" not in data:
        return None

    return {
        "heartrate": data["heartrate"]["data"],
        "time": data["time"]["data"],
        "distance": data["distance"]["data"],  # meters
    }


# calc zone data
# heavily vibe coded
# Notes on feature engineering done:
# - Often during workouts, between reps, runner will be standing around
#   resting. This can drag down the pace_in_z4 and not reflect the load
#   actually experienced, so we want to exclude rest. We still want to 
#   include rests in time_in_z4 to correctly attribute the stimulus.
# - Moving threshold is set to 1.4m/s == 12min/km
def compute_zone_metrics(streams, moving_threshold=1.4):
    hr_data = streams["heartrate"]
    time_data = streams["time"]
    dist_data = streams["distance"]

    zone_time = {z: 0 for z in ZONES}       # minutes, will convert later
    zone_distance = {z: 0 for z in ZONES}   # meters, only moving
    moving_time = {z: 0 for z in ZONES}     # seconds of actual movement

    for i in range(1, len(hr_data)):
        hr = hr_data[i]
        dt = time_data[i] - time_data[i - 1]
        dd = dist_data[i] - dist_data[i - 1]
        speed = dd / dt if dt > 0 else 0

        pct = hr / MAX_HEART_RATE

        for z, (low, high) in ZONES.items():
            if low <= pct < high:
                zone_time[z] += dt                  # always count all time
                if speed >= moving_threshold:
                    zone_distance[z] += dd
                    moving_time[z] += dt
                break

    zone_pace = {}
    for z in ZONES:
        if zone_distance[z] > 0:
            pace_sec_per_m = moving_time[z] / zone_distance[z]  # sec per meter over moving segments
            pace_min_per_km = (pace_sec_per_m * 1000) / 60
            zone_pace[z] = pace_min_per_km
        else:
            zone_pace[z] = None

        # convert zone_time to minutes for consistency
        zone_time[z] = zone_time[z] / 60

    return zone_time, zone_pace


# insert into SQLite db
def insert_runs_to_db(runs, token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for run in runs:
        if run['type'] != 'Run':
            continue

        activity_id = run['id']
        streams = fetch_streams(token, activity_id)

        if streams:
            zone_times, zone_paces = compute_zone_metrics(streams)
        else:
            zone_times = {z: None for z in ZONES}
            zone_paces = {z: None for z in ZONES}

        if run['moving_time'] > 0 and run['distance'] > 0:
            distance_km = run['distance'] / 1000            # km
            duration_min = run['moving_time'] / 60          # minutes
            pace = duration_min / distance_km               # min/km
        else:
            distance_km = 0
            duration_min = 0
            pace = None

        c.execute('''
            INSERT OR REPLACE INTO runs (
                id, name, start_date, distance, duration, pace,
                elevation_gain, type,
                time_z1, time_z2, time_z3, time_z4, time_z5,
                pace_z1, pace_z2, pace_z3, pace_z4, pace_z5
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            activity_id,
            run['name'],
            run['start_date'],
            distance_km,
            duration_min,
            pace,
            run['total_elevation_gain'],
            run['type'],
            zone_times["z1"],
            zone_times["z2"],
            zone_times["z3"],
            zone_times["z4"],
            zone_times["z5"],
            zone_paces["z1"],
            zone_paces["z2"],
            zone_paces["z3"],
            zone_paces["z4"],
            zone_paces["z5"],
        ))

        print(f"Processed run {activity_id}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    token = get_access_token()
    runs = fetch_activities(token, per_page=NUMBER_OF_RUNS_TO_FETCH)
    insert_runs_to_db(runs, token)



# Some helper code to check table
# conn = sqlite3.connect(DB_PATH)
# conn.row_factory = sqlite3.Row
# c = conn.cursor()

# c.execute("SELECT * FROM runs ORDER BY start_date DESC LIMIT ?", (100,))
# rows = c.fetchall()

# for row in rows:
#     print(f"Run ID: {row['id']}, Name: {row['name']}, Date: {row['start_date']}")
#     print(f"  Distance: {row['distance']:.2f} km, Duration: {row['duration']:.1f} min, Pace: {row['pace']:.2f} min/km")
#     print(f"  Elevation gain: {row['elevation_gain']:.1f} m, Type: {row['type']}")
#     print("  Time in zones (min):", end=" ")
#     print(", ".join(f"{row[f'time_{z}']:.1f}" if row[f'time_{z}'] else "None" for z in ['z1','z2','z3','z4','z5']))
#     print("  Pace in zones (min/km):", end=" ")
#     print(", ".join(f"{row[f'pace_{z}']:.2f}" if row[f'pace_{z}'] else "None" for z in ['z1','z2','z3','z4','z5']))
#     print("-" * 60)

# conn.close()
