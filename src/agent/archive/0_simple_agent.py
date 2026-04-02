from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.runtime import get_runtime


load_dotenv()
BASE_DIR = Path('C:/Users/User/Documents/Repositories/personal_ai_running_coach')

# ---- Database ----
# Define SQL database, and context for agent
DB_PATH = BASE_DIR / "data" / "strava.db"
db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")


@dataclass
class RuntimeContext:
    db: SQLDatabase

SUMMARY_PATH = BASE_DIR / "schema_summary.txt"
with open(SUMMARY_PATH, "r") as f:
    DB_SCHEMA = f.read()


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
    
# --- System prompt ----
SYSTEM_PROMPT = f"""
You are an expert running coach and careful SQLite analyst.

You have access to a SQLite database of running activities, with two tables - `runs` and `weekly_summary`.

DATABASE SCHEMA:
{DB_SCHEMA}

Rules:
- Think step-by-step.
- When you need data, call the tool `execute_sql` with ONE SELECT query.
- Read only; NEVER modify the database (no INSERT/UPDATE/DELETE/etc).
- Always LIMIT results to 5 unless explicitly needed.
- Prefer explicit column names (avoid SELECT *).
- If the tool returns 'Error:', fix your SQL and retry.
- When you know the correct SQL query, do not call execute_sql more than once per question.

Additional rules on interpreting requests and data:
- Use the schema to understand:
  - distance is in km
  - duration is in minutes
  - pace is in min/km
- Refer to `runs` for full history, and `weekly_summary` for an overview of weekly volume and progress. 
- Use race performances as a measure of fitness progression, as well as volume and average pace in HR zones.
- The data is from Strava, and distances and paces may not be exact. Apply a degree of tolerance - e.g. if asked to look at 5K race performance, allow for distance between 4.8 and 5.2.

Coaching rules:
- If receiving a request about training plans or how current fitness might translate, ALWAYS check recent race performances or fastest efforts, to benchmark fitness first. Also consider recent mileage.
- Be specific and actionable.
"""

# --- Define agent ---
agent = create_agent(
    model="openai:gpt-4o-mini",  # upgrade from 3.5, much better reasoning
    tools=[execute_sql],
    system_prompt=SYSTEM_PROMPT,
    context_schema=RuntimeContext,
)


# --- Query agent ----
question = "YOUR_QUESTION"

for step in agent.stream(
    {"messages": question},
    context=RuntimeContext(db=db),
    stream_mode="values",
    max_tokens=300
):
    step["messages"][-1].pretty_print()