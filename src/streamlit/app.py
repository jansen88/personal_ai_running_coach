import streamlit as st
import uuid

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)

from src.utils.fetch_from_strava_api import get_access_token, fetch_activities, insert_runs_to_db
from src.agent.agent import build_agent, runtime_context


st.set_page_config(page_title="AI Running Coach!", layout="wide")

# this is a weird way to set button colour but there's only 1 and it works
st.markdown(
    """
    <style>
    /* Style + size for primary button (Strava button) */
    div.stButton > button[kind="primary"] {
        background-color: #ff5a00 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;

        height: 56px !important;          /* match chat input */
        width: 100% !important;
    }

    /* Hover */
    div.stButton > button[kind="primary"]:hover {
        background-color: #e14e00 !important;
    }

    /* Active */
    div.stButton > button[kind="primary"]:active {
        background-color: #c84300 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# initialize session state
if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "debug" not in st.session_state:
    st.session_state.debug = []

# UI: panels
chat_col, debug_col = st.columns([3, 2], vertical_alignment="top")

# UI >> Left panel >> Elements
with chat_col:
    st.title("🤖 AI Running Coach 🏃")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    button_col, input_col,  = st.columns([1, 4])
    
    with input_col:
        prompt = st.chat_input("Ask your coach...")

    with button_col:
        data_button = st.button("Fetch Strava data", type="primary")

    # >> Back end
    if data_button:
                st.info("Fetching Strava data...")
                try:
                    token = get_access_token()
                    runs = fetch_activities(token, per_page=40)
                    insert_runs_to_db(runs, token)
                    st.success(f"Fetched {len(runs)} runs from Strava!")
                except Exception as e:
                    st.error(f"Error fetching data: {e}")

    if prompt:
        # append user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # --- Run agent stream ---
        response_content = ""
        st.session_state.debug.append("Starting agent stream...")

        # Collect full debug separately
        full_debug = []

        for chunk in st.session_state.agent.stream(
            {"messages": prompt},
            {"configurable": {"thread_id": st.session_state.thread_id}},
            context=runtime_context,       # shared DB/runtime
            stream_mode="values",
            max_tokens=300,
        ):
            # append each chunk to debug
            full_debug.append(chunk)
            st.session_state.debug.append(chunk)  # update RHS panel

            # update final response content only at the end
            response_content = chunk["messages"][-1].content

        # append final assistant response only
        st.session_state.messages.append({"role": "assistant", "content": response_content})

        # display final answer in chat
        with st.chat_message("assistant"):
            st.markdown(response_content, unsafe_allow_html=True)

# UI >> Right panel >> Elements
with debug_col:
    st.subheader("Debug (Developer only)")

    st.markdown(
        """
        <style>
        .stApp .streamlit-expanderContent p,
        .stApp .stText {
            color: #333333;  /* dark grey */
        }
        </style>
        """,
        unsafe_allow_html=True,
    ) 

    # only show last 20 debug entries else longgggg
    for d in st.session_state.debug[-20:]:
        st.text(d)