# Personalised AI Running Coach

## Overview
This document serves as design documentation, with an initial brain dump of what I could build, covering:
- Use case
- Tools (for agent to have access to)
- Reasoning loop / agent workflow
- Technical design

## Use case
Users interact with agent with functionality to:
- Ask questions about recent runs and running trends
    - "How is my training volume?"
    - "Is my fitness improving?"
    - "What's my fastest 5k in the last month?"
- Request training plans
    - "Create a weekly plan to run a sub 19 5k in 8 weeks."
    - "Accounting for rain and heat this week, create a training plan for this week's runs."
    - "Revise training plan to incorporate a Norwegian singles approach..."

Other optional higher effort use cases:
- Report and update progress against training plan [Higher effort, have to save down training plan / remember conversation?]
- Integrate with Google Calendar, so can plan around work, calendar blocks, public holidays where I'm free etc.

## Tools
Thinking about the tools our agent needs to have access to, in order to be able to fulfil above use case:
- Strava API tool [Pre-load the data, but give agent option to update]
    - Need to look into how to set this up, what info available, and how to structure it
    - Also need to think about how to manage the info we get such that token consumption is reasonable i.e. don't pull ALL historic data, format etc
- Weather API tool
    - Would be good to build in, to tailor the training plan
- Standardised query tool
    - For the agent to be able to query the data - probably SQLite db + SQL
- Planner tool
    - Outputs structured weekly schedules in standard format??
- RAG tool 
    - Take some quality articles / information on training, and save to vector store for agent to retrieve relevant information from

## Reasoning loop
Want to have agent work something like the below:
0. Retrieve necessary data
    - Strava API -- recent activities (last 6 weeks)
    - Weather API -- weather for week ahead
    - Preprocessing as needed to minimise token consumption for LLM
    - Also include a markdown file for the agent to have access to, which tells it what the structure of the data is?
1. Receive human message with goal or question. 
    - Decide which tools to call next -- is Planner tool needed, or just perform retrieval / analysis
    - Also check clarity / completeness, and ask clarifying questions as needed. Especially for training plan, should be clear on acceptable volume, how many hard sessions per week, etc.
2. Clarifying step if needed (ask follow up questions)
3. Analysis and reasoning
    - Decide what past data is relevant to answering question
    - Analyse training approach, consistency and progression
    - Construct response / plan
4. Output - message or structured output for training plan
5. Memory - use for responding to follow-up questions

## Technical consideratons
- APIs
    - Strava API
    - Weather API -- BOM?
- Preprocessing data
    - Want to convert this to some structured format, which is also token efficient
        - Pandas dataframe -- ChatGPT says ok option for small data, but agents are better at reliably prompting SQL than pandas which makes sense
        - SQLite database -- ChatGPT says best option. "stable, predictable query interface that works with natural language -> SQL abstraction"
        - JSON -- easy but not efficient for querying?
- LLM / LangChain
    - Model - what model to use? Balance reasoning vs cost. ChatGPT sugggests GPT-4-turbo because of good reasoning. 3.5-turbo might also be fine if cost is a concern?
    - LangChain agent to use - there are a few options (Tool-Using Agent, StructuredChatAgent, ReAct agents). My experience is with ReAct so probably just do that
    - Memory
- Deployment
    - Might want to wrap this all up into a Streamlit app or something so we have a nice dashboard too. ChatGPT can probably do this
