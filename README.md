# Personalised AI Running Coach
Hobby project creating an AI running coach with personalised training plans using my Strava data. The purpose of this was for personal use, and also as a practical hobby exercise working with LangChain.

## Setup
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