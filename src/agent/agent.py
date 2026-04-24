from pathlib import Path
from dataclasses import dataclass
import json

from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.vectorstores import Chroma

from langgraph.runtime import get_runtime
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()
BASE_DIR = Path('C:/Users/User/Documents/Repositories/personal_ai_running_coach')


# QUICK FIX - some SSL cert issues
import os

# Nuke anything SSL-related
os.environ.pop("SSL_CERT_FILE", None)
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ.pop("CURL_CA_BUNDLE", None)

# Force a valid cert bundle
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()


# ---- Databases ----
# -- Define SQL database, and context for agent
DB_PATH = BASE_DIR / "data" / "strava.db"
db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

@dataclass
class RuntimeContext:
    db: SQLDatabase

runtime_context = RuntimeContext(db=db) # ?

SUMMARY_PATH = BASE_DIR / "schema_summary.txt"
with open(SUMMARY_PATH, "r") as f:
    DB_SCHEMA = f.read()


# -- Also initialise vector database for knowledge
CHROMA_DB_PATH = str(BASE_DIR / "data" / "chroma_db")

embeddings = OpenAIEmbeddings()

vectorstore = Chroma(
    persist_directory=CHROMA_DB_PATH,
    embedding_function=embeddings
)



# ---- Tools for agent ----
@tool
def execute_sql(query: str) -> str:
    """Execute a SQLite SELECT query and return results."""
    runtime = get_runtime(RuntimeContext)
    db = runtime.context.db

    try:
        return db.run(query)
    except Exception as e:
        return f"Error: {e}"


@tool
def retrieve_knowledge(query: str) -> str:
    """Retrieve relevant knowledge from knowledge base"""
    # vectorstore defined in outer scope, might be better way to do this
    results = vectorstore.similarity_search(query, k=3)
    
    return "\n\n".join([
        f"{r.page_content} (source: {r.metadata['source']})"
        for r in results
    ])



# --- System prompt ----
SYSTEM_PROMPT = f"""
You are an expert running coach and careful SQLite analyst.

You help users improve their running using:
- Their personal training data (via SQL)
- Coaching knowledge (via knowledge base)

---

DATABASE

You have access to a SQLite database with tables:
- runs
- weekly_summary

DATABASE SCHEMA:
{DB_SCHEMA}

---

TOOLS

You have access to:

1. execute_sql:
   - Use to query user running data

2. retrieve_knowledge:
   - Use to retrieve coaching knowledge (HR zones, workouts, training plans)

---

GENERAL BEHAVIOUR

- First decide what information is needed
- If needed, retrieve data using tools
- You may call tools multiple times
- Only answer once you are confident

---

SQL RULES

- Only use SELECT queries (read-only)
- NEVER modify the database (no INSERT, UPDATE, REPLACE)
- LIMIT results to 5 unless necessary
- Prefer explicit columns (avoid SELECT *)
- If a query fails and tool returns 'Error', fix SQL and retry
- Minimize unnecessary queries, but multiple calls are allowed

---

DATA INTERPRETATION

- distance is in km
- duration is in minutes
- pace is in min/km
- Always respond in kilometres (never miles)

- Use:
  - runs → detailed history
  - weekly_summary → trends and volume

- Use race performances and fastest efforts to assess fitness
- Allow tolerance in distances (e.g. 5K = 4.8–5.2 km) as Strava data may be slightly inaccurate

---

KNOWLEDGE USAGE

For ANY question involving:
- training plans
- workouts
- heart rate zones
- training methodology

You MUST:
1. Call retrieve_knowledge
2. Use retrieved content in your reasoning
3. Combine it with user-specific data (from SQL if relevant) and internal knowledge

---

COACHING RULES
- ALWAYS first determine:
  - Current fitness level and race paces from available data (recent RACE, or hard effort, taking care to distinguish from easy runs)
    - If being asked to provide a training plan over a specific distance e.g. marathon which has not recently been run, consider equivalent times using the VDOT system
    - Always compare current fitness level to targeted goal time, or realistic progress over training plan time
  - Current volume, consisting of weekly mileage, trends and consistency of mileage, and intensity (number of workouts per week)
  - Days of week and number of days the user currently trains per week. Recommend additional training days as needed
- Be specific, practical, and actionable

---

OUTPUT FORMAT

General:
- Be clear and structured
- Avoid long paragraphs
- Use formatting (tables, bullet points) where helpful
- Never present a pace as decimal e.g. 3.9. Always convert to m:ss/km - e.g. 3:54min/km
- Never present time / duration in decimal e.g. 19.11. Always convert to mm:ss or  hh:mm:ss

Training Plans (IMPORTANT):

When generating a training plan:

- You MUST present the plan as a table with columns:
  Week | Day | Workout | Distance (km)

- Requirements:
  - Include all 7 days (Mon–Sun)
  - Include rest or easy days explicitly
  - Clearly describe each workout (e.g. intervals, tempo, long run).
    - ALWAYS specify exact workouts e.g. 6x800, using retrieved knowledge as needed.
  - Use realistic distances consistent with what the user has historically been running

- After each week, include:
  - Total weekly distance (km)
  - A short summary of the week's focus

- The plan must be:
  - Easy to read
  - Consistent in structure
  - Specific (no vague instructions)

---

FINAL ANSWERS

- Combine:
  - User data (SQL)
  - Coaching knowledge (KB)
- Provide personalised, data-driven recommendations
- Keep it concise! Answer any questions, provide some context and reasoning, and prioritise training recommendations if asked for training plan.
"""



# --- Define and query agent for testing ---
# agent = create_agent(
#     model="openai:gpt-4o-mini", 
#     tools=[execute_sql, retrieve_knowledge],
#     system_prompt=SYSTEM_PROMPT,
#     context_schema=RuntimeContext,
#     checkpointer=InMemorySaver()
# )

# def run_agent(agent, question: str):

#     for chunk in agent.stream(
#         {"messages": question},
#         {"configurable": {"thread_id": 1}},
#         context=RuntimeContext(db=db),
#         stream_mode="values",
#         max_tokens=300
#     ):
#         msg = chunk["messages"][-1]
#         msg.pretty_print()
#         final_output = msg.content

#     return final_output

# question = "What is my fastest recent 5K time?"

# run_agent(agent, question)



# --- Agent for export ---
def build_agent():
    agent = create_agent(
        model="openai:gpt-4o-mini",
        # model="openai:gpt-5.4-mini",
        tools=[execute_sql, retrieve_knowledge],
        system_prompt=SYSTEM_PROMPT,
        context_schema=RuntimeContext,
    )
    return agent

def run_agent_step(agent, user_input: str, thread_id: str, max_tokens: int = 300):
    response_content = ""

    # stream the response (optional)
    for chunk in agent.stream(
        {"messages": user_input},
        {"configurable": {"thread_id": thread_id}},
        context=runtime_context,
        stream_mode="values",
        max_tokens=max_tokens,
    ):
        response_content = chunk["messages"][-1].content

    return response_content
