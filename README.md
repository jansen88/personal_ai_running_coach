# Personalised AI Running Coach
Hobby project creating an AI running coach with personalised training plans using my Strava data. The purpose of this was for personal use, and also as a practical hobby exercise working with LangChain.

## Overview
To fill in

## 🗒️ Detailed notes
- **API dependencies** - requires API keys for Strava (free) and OpenAI (paid)
    - Note # of API calls to Strava is N+1, where N is number of runs fetched as we need the more detailed HR data per run
    - I didn't set this up to use other models or servers, but obviously this could be done.
- **Preprocessing of Strava data** - dictionary returned from API is saved as SQLite database
    - SQLite database enables standardised, performant querying by agent
    - Data dictionary - See `database_schema.json` for schema. This is passed to the agent.
    - Data on time / pace by HR zone:
        - HR zones configured in `src/config.py`
        - Some (vibe coded) effort has gone into summarising statistics by HR zone, to provide better information for the agent to work with.
- **Agent**
    - Development log:
        | Agent description | Tools | Improvements made | What it was able to do | Reference |
        | --- | --- | --- | --- | --- |
        | Simple agent, chatbot able to query Strava data | `execute_sql`: Execute SQL commands and return result | (a) Providing schema - Providing the database schemas to the system prompt removed SQL errors altogether <br> (b) Feature engineering - Summarising time / pace by HR zone, identifying races to serve as fitness indicators and adding a weekly summary significantly improved response quality by increasing personalisation / relevance <br> (c) Improving system prompt - Adding specific instructions such as always referring to runs tagged as fitness indicators for a benchmark notably improved response quality. |Answer questions such as fastest / longest runs and report on fitness trends. Provided reasonable training plans, appropriately accounting for current fitness. | `notebooks/0_simplest_agent.ipynb` |
        | ... | ... | (a) Introduced structured decomposition to plan work i.e. instead of user -> agent -> tool -> answer, user -> planner -> steps -> executor -> tools -> answer | ... | ... |

## 🔧 Setup
First, set up **Python environment**
For Windows and in Bash, change directory to this repo and:
1. Create Python virtual env
```
conda create -n ai_running_coach_env python=3.13
```
2. Activate virtual env
```
conda activate ai_running_coach_env
```

Check it's active
```
which python
```
3. Install requirements
```
pip install -r requirements.txt
```

Then set up API keys for OpenAI (I've used this) and Strava:
4. Set up OpenAI API key
- Get API key (platform.openai.com)
- Add to .env file 
```
OPENAI_API_KEY=...
```

To check:
```
import os
os.getenv("OPENAI_API_KEY")
```

5. Set up Strava API key
- Get Strava API key from [here](https://developers.strava.com/)
- Add to .env file
```
STRAVA_CLIENT_ID=218981
STRAVA_CLIENT_SECRET=eebd6d8728726e3f3b4eae612791a0002d6b5a4a
STRAVA_REFRESH_TOKEN=4a822ac443756ff381b712e7444084fd443c0ad2
```
- There were some extra steps I had to follow to get a valid refresh token:
    - Open URL below in browser, replacing Client ID
    https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
    - Authorise, which will direct you to a link as below. Take the code=abc123xyz part
    http://localhost/?state=&code=abc123xyz&scope=read,activity:read_all
    - Run the Python code below to get a valid refresh token, and update this in .env
    ```
    import requests

    url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': 'PASTE_CODE_HERE',
        'grant_type': 'authorization_code'
    }

    res = requests.post(url, data=payload)
    print(res.json())
    ```

6. **Initialise databases** if needed
- To initialise the SQLite database, check a `data` folder exists (it should if cloning this repo). If not, please create it. Then run the initalisation script
```
python src/utils/initialise_sqlite_db.py
```
- To initialise the SQLite database for Strava data (this will get built into the agent, but can also be done manually):
```
python src/utils/fetch_from_strava_api.py
```
- To initialise the Chroma vector database of running knowledge (from web pages):
```
python src/utils/create_vector_store.py
```


7. Other
Please also update `src/config.py` with your personalised HR zones as needed.
```
# Define HR zones
# We get the HR data from Strava API, then need your HR zone definitions below
MAX_HEART_RATE = 200

ZONES = {
    "z1": (0, 0.6),
    "z2": (0.6, 0.75),
    "z3": (0.75, 0.85),
    "z4": (0.85, 0.95),
    "z5": (0.95, 1.0),
}
```