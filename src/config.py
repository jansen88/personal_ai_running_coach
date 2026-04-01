import os
from dotenv import load_dotenv

load_dotenv()


STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

NUMBER_OF_RUNS_TO_FETCH = 40



BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'strava.db')



# Web pages to grab for RAG system
WEB_URLS = [
    "https://www.reddit.com/r/artc/comments/6qrk62/dissecting_daniels_chapter_two_physiology_of/?utm_content=title&utm_medium=user&utm_source=reddit&utm_name=u_CatzerzMcGee",
    "https://www.reddit.com/r/artc/comments/6s7jux/dissecting_daniels_part_3_training_intensities/",
    "https://www.mcmillanrunning.com/best-5k-workout/",
    "https://www.reddit.com/r/running/wiki/marathon_training_plans/",
    "https://www.halhigdon.com/training-programs/marathon-training/intermediate-2-marathon/",
    "https://www.halhigdon.com/training-programs/marathon-training/novice-supreme/",
    "https://www.runnersworld.com/advanced/a20819355/marathon-advantage/?page=single"
]



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