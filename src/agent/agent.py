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


# ---- Databases ----
# -- Define SQL database, and context for agent
DB_PATH = BASE_DIR / "data" / "strava.db"
db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

@dataclass
class RuntimeContext:
    db: SQLDatabase

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

You have access to a SQLite database of running activities, with two tables - `runs` and `weekly_summary`.

DATABASE SCHEMA:
{DB_SCHEMA}

You also have access to a knowledge base with information on HR training zones, and training plans / workouts, that you can access with the tool `retrieve_knowledge`.

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
- Always respond in kilometres. NEVER respond in miles.

Coaching rules:
- If receiving a request about training plans or how current fitness might translate, ALWAYS check recent race performances or fastest efforts, to benchmark fitness first. Also consider recent mileage.
- Be specific and actionable.

Knowledge usage rules:
- For ANY question involving:
  - training plans
  - workouts
  - heart rate zones
  - training structure or methodology

You MUST call `retrieve_knowledge` before answering.

- Combined your internal knowledge with retrieved knowledge, preferencing retrieved knowledge.
- You should combine retrieved knowledge with user-specific data from SQL.
"""



# --- Define and query agent ---
agent = create_agent(
    model="openai:gpt-4o-mini", 
    tools=[execute_sql, retrieve_knowledge],
    system_prompt=SYSTEM_PROMPT,
    context_schema=RuntimeContext,
    checkpointer=InMemorySaver()
)

def run_agent(agent, question: str):

    for chunk in agent.stream(
        {"messages": question},
        {"configurable": {"thread_id": 1}},
        context=RuntimeContext(db=db),
        stream_mode="values",
        max_tokens=300
    ):
        msg = chunk["messages"][-1]
        msg.pretty_print()
        final_output = msg.content

    return final_output

# question = "YOUR_QUESTION"

run_agent(agent, question)
