import os
from dotenv import load_dotenv

load_dotenv()


STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

NUMBER_OF_RUNS_TO_FETCH = 40



BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'strava.db')



# Define HR zones
# We get the HR data from Strava API, then need your HR zone definitions below
MAX_HEART_RATE = 200

ZONES = {
    "z1": (0, 0.7),
    "z2": (0.7, 0.8),
    "z3": (0.8, 0.88),
    "z4": (0.88, 0.94),
    "z5": (0.94, 1.0),
}