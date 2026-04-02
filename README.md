# Personalised AI Running Coach
Hobby project creating an AI running coach with personalised training plans using my Strava data. The purpose of this was for personal use, and also as a practical hobby exercise working with LangChain.

<img width="1617" height="837" alt="image" src="https://github.com/user-attachments/assets/caf1b5fe-6173-447b-a324-d97a325243cb" />

## Overview
This is an LLM application, which acts as an AI running companion by analysing your Strava data, providing insights on your fitness, and providing personalised running plans.

The application consists of an AI agent with tools to execute queries on a SQLite database (structured data from Strava API), and retrieve relevant training informatoin from a knowledge base of curated web articles. The user interacts with the AI agent through a Streamlit app interface. 

The application is a working MVP, and could be further improved (see development log below).

You will need to set up OpenAI and Strava API keys (obviously) to run this - see setup instructions below.

## 🗒️ Development log
- Initialised agent with basic tool `execute_sql` to execute SQL commands and return result
- Prompt tuning
    - Providing the database schema to system prompt removed SQL errors entirely
    - Adding specific instructions to refer to runs tagged as fitness indicators for benchmarks, or allow for tolerance in run distances (4.98km is a 5k) added a layer of human heuristics which improved results
    - ChatGPT quite good at generating improved prompt when specific issue raised
- Feature engineering: refining the information provided to the agent by summarising time / pace in HR zone to better reflect training load, tagging races to serve as fitness indicators and adding weekly summaries to more easily extract views of progress significantly improved response quality (more personalised, less generic) 
- Tested separated planning (decomposition of question into distinct tasks first) into a separate LLM call, as an attempt at more complex orchestration. Did not perform well as <br>
    (a) key information from the system prompt was being lost and in the planner prompt <br>
    (b) more overhead was needed to ensure the agent was clear on the overall plan at each step, and <br>
    (c) error handling also required additional overhead i.e. if SQL error, need to run more steps so needed to override the original plan. <br>
My experience was that for this task, the agent was already independently managing the required steps well, and didn't need the planning separated, so I abandoned this.
- Added knowledge base with articles on HR training zones, training plans and workouts. Implemented simple RAG system by fetching text from web pages, chunking and saving embeddings to vector database, and prompting agent to retrieve from knowledge base as needed via the tool `retrieve_knowledge`.
    - I think could improve the agent a lot by choosing the right articles, with most relevant training approaches to what I have been following. Could directly include good training plans for 5K, HM, Marathon etc. to produce good specific recommendations.
- Choice of model
    - gpt-4o-mini: Seems to be very good at instruction following. Reasoning is weaker - notice this in training plans
    - gpt-5.4-nano: Much better reasoning, but ignores my instructions!
    - gpt-5.4-mini: Did better job of following instructions and reasoning (sensible plan), but more expensive.

Other ideas
- Functionality to save down training plans in standardised format, and track training against
- Long-term memory for goals, races etc.
- Weather API - especially in summer, training plans vary a lot depending on heat / humidity! My workout will definitely be slower if its hot!

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
STRAVA_CLIENT_ID=xxx
STRAVA_CLIENT_SECRET=xxxx
STRAVA_REFRESH_TOKEN=xxxx
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
