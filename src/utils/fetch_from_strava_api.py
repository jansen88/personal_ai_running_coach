# Developer notes:
# - Assumes Strava API keys and OAuth set up (see README)
# - Scrapes last N activities (1 API call)
# - Then fetches streams per activity (N API calls)
# - Computes time in HR zones + pace per zone
# - Strava rate limits: 100 requests / 15 mins, 1000 daily
# - A lot of vibe coded feature engineering to produce HR zone summaries, and weekly summaries
# TODO: Need to manage average pace in a nicer way - currently represented as 3.9 min/km instead of 3:54min/km.

import requests
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)
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


# fetch all runs
def fetch_activities(token, per_page):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f'Bearer {token}'}
    params = {'per_page': per_page}
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()


# fetch details per run
def fetch_streams(token, activity_id):
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {'Authorization': f'Bearer {token}'}
    params = {"keys": "heartrate,time,distance", "key_by_type": "true"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200: return None
    data = res.json()
    if "heartrate" not in data or "distance" not in data or "time" not in data:
        return None
    return {"heartrate": data["heartrate"]["data"],
            "time": data["time"]["data"],
            "distance": data["distance"]["data"]}



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

    zone_time = {z: 0 for z in ZONES}       
    zone_distance = {z: 0 for z in ZONES}   
    moving_time = {z: 0 for z in ZONES}     

    for i in range(1, len(hr_data)):
        hr = hr_data[i]
        dt = time_data[i] - time_data[i - 1]
        dd = dist_data[i] - dist_data[i - 1]
        speed = dd / dt if dt > 0 else 0
        pct = hr / MAX_HEART_RATE
        for z, (low, high) in ZONES.items():
            if low <= pct < high:
                zone_time[z] += dt
                if speed >= moving_threshold:
                    zone_distance[z] += dd
                    moving_time[z] += dt
                break

    zone_pace = {}
    for z in ZONES:
        if zone_distance[z] > 0:
            pace_sec_per_m = moving_time[z] / zone_distance[z]
            zone_pace[z] = (pace_sec_per_m * 1000) / 60
        else:
            zone_pace[z] = None
        zone_time[z] /= 60  # convert to minutes

    return zone_time, zone_pace


# classify run type
# pretty crude definitions
def classify_run(zone_time):
    total_moving = sum(zone_time.values())
    z4_or_5_time = zone_time["z4"] + zone_time["z5"]
    if z4_or_5_time > 0.3 * total_moving or z4_or_5_time  > 15:
        return "Threshold"
    elif zone_time["z3"] > 0.3 * total_moving or zone_time["z3"] > 15:
        return "Tempo"
    else:
        return "Base"


# check if run is a race
# valid distances I've considered - 5k, 10k, HM, Mara
# and added a tolerance of 5% because strava / gps error...
def is_race(distance, zone_time):
    race_distances = [5,10,21.1,42.2]
    tolerance = 0.05
    total_moving = sum(zone_time.values())
    high_intensity = zone_time["z4"] + zone_time["z5"]
    if any(abs(distance - rd) / rd < tolerance for rd in race_distances) and high_intensity > 0.5 * total_moving:
        return True
    return False


def insert_runs_to_db(runs, token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for run in runs:
        if run['type'] != 'Run': continue
        activity_id = run['id']
        streams = fetch_streams(token, activity_id)
        if streams:
            zone_times, zone_paces = compute_zone_metrics(streams)
        else:
            zone_times = {z: 0 for z in ZONES}
            zone_paces = {z: None for z in ZONES}

        if run['moving_time'] > 0 and run['distance'] > 0:
            distance_km = run['distance'] / 1000
            duration_min = run['moving_time'] / 60
            pace = duration_min / distance_km
        else:
            distance_km = 0
            duration_min = 0
            pace = None

        # new columns
        run_type = classify_run(zone_times)
        race_flag = is_race(distance_km, zone_times)
        start_dt = datetime.fromisoformat(run['start_date'].replace("Z","+00:00"))
        week_start_dt = start_dt - timedelta(days=start_dt.weekday())
        week_start = week_start_dt.strftime("%Y-%m-%d")

        c.execute('''
            INSERT OR REPLACE INTO runs (
                id, name, start_date, distance, duration, pace,
                elevation_gain, type,
                time_z1, time_z2, time_z3, time_z4, time_z5,
                pace_z1, pace_z2, pace_z3, pace_z4, pace_z5,
                run_type, is_race, week_start
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            run_type,
            race_flag,
            week_start
        ))
        print(f"Processed run {activity_id}")

    conn.commit()

    # --- compute weekly_summary ---
    # basically an ETL step in Python
    # super vibe coded
    df = pd.read_sql_query("SELECT * FROM runs", conn)

    if not df.empty:
        # ensure no NaNs break masks
        df["run_type"] = df["run_type"].fillna("Base")
        df["duration"] = df["duration"].fillna(0)
        df["pace"] = df["pace"].fillna(0)
        df["is_race"] = df.get("is_race", False).fillna(False)
        
        # ensure week/year columns exist
        df["start_date"] = pd.to_datetime(df["start_date"])
        df["week_start"] = (
            df["start_date"] - pd.to_timedelta(df["start_date"].dt.weekday, unit="d")
        ).dt.strftime("%Y-%m-%d")

        weekly = df.groupby(["week_start"])
        summaries = []

        for week_start, g in weekly:
            week_start = (
                g["start_date"].min() - pd.to_timedelta(g["start_date"].min().weekday(), unit="d")
            ).strftime("%Y-%m-%d")

            total_distance = g["distance"].sum()
            total_time = g["duration"].sum()

            weighted_sum_base = (g["pace_z1"].fillna(0) * g["time_z1"].fillna(0)).sum() + \
                                (g["pace_z2"].fillna(0) * g["time_z2"].fillna(0)).sum()
            time_easy = g["time_z1"].sum() + g["time_z2"].sum()
            avg_pace_base = weighted_sum_base / time_easy if time_easy > 0 else None

            tempo_mask = g["time_z3"] >= 4
            time_z3 = g.loc[tempo_mask, "time_z3"].sum()
            avg_pace_z3 = (
                (g.loc[tempo_mask, "pace_z3"].fillna(0) * g.loc[tempo_mask, "time_z3"].fillna(0)).sum()
                / time_z3 if time_z3 > 0 else None
            )

            thresh_mask = (g["time_z4"] >= 4) | (g["time_z5"] >= 4)
            time_z4_or_5 = g.loc[thresh_mask, "time_z4"].sum() + g.loc[thresh_mask, "time_z5"].sum()
            avg_pace_z4_or_5 = (
                (
                    g.loc[thresh_mask, "pace_z4"].fillna(0) * g.loc[thresh_mask, "time_z4"].fillna(0) +
                    g.loc[thresh_mask, "pace_z5"].fillna(0) * g.loc[thresh_mask, "time_z5"].fillna(0)
                ).sum() / time_z4_or_5 if time_z4_or_5 > 0 else None
            )

            num_races = g["is_race"].sum()
            num_races = int(num_races)

            race_summary = ", ".join([
                f"{round(r['distance'],1)}K in {r['duration']:.1f}min"
                for _, r in g.loc[g["is_race"].astype(bool), :].iterrows()
            ]) if num_races > 0 else ""

            summaries.append((
                week_start, total_distance, total_time,
                time_easy, time_z3, time_z4_or_5,
                avg_pace_base, avg_pace_z3, avg_pace_z4_or_5,
                num_races, race_summary
            ))

        # insert/update weekly_summary
        c.executemany('''
            INSERT OR REPLACE INTO weekly_summary (
                week_start, total_distance, total_time, time_easy, time_z3, time_z4_or_5,
                avg_pace_base, avg_pace_z3, avg_pace_z4_or_5, num_races, race_summary
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', summaries)
        conn.commit()

    conn.close()

if __name__ == "__main__":
    token = get_access_token()
    runs = fetch_activities(token, per_page=NUMBER_OF_RUNS_TO_FETCH)
    insert_runs_to_db(runs, token)






# # Some helper code to check table
# conn = sqlite3.connect(DB_PATH)
# runs = pd.read_sql_query("SELECT * FROM runs", conn)
# weekly = pd.read_sql_query("SELECT * FROM weekly_summary", conn)
# conn.close()