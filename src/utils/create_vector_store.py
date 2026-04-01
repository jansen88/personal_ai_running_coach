# For some specified pages, create vector DB with Chroma for RAG system

import json
import re
import os

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)
from src.config import (
    WEB_URLS
)


DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/chroma_db')

# TODO main could be a lot cleaner
if __name__ == "__main__":
    
    docs = []

    for url in WEB_URLS:
        loader = WebBaseLoader(url)
        loaded = loader.load()
        docs.extend(loaded)


    # Some cleaning, didn't manage to get rid of all of the \n so probably could clean more
    clean_docs = []

    def clean_text(text: str) -> str:
        return (
            text.replace("\n\n", "\n")
                .replace("\t", " ")
                .strip()
        )

    for d in docs:
        cleaned = clean_text(d.page_content)
        clean_docs.append({
            "text": cleaned,
            "source": d.metadata.get("source", "unknown")
        })

    # We want to condense all this text into useful knowledge
    # to improve our RAG system. For this use case, fine to
    # get LLM-generated summaries!
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    CONDENSE_PROMPT = """
    You are an expert running coach.

    Extract 5–10 key training insights from the text below.

    Each insight should:
    - be self-contained
    - be 50–150 words
    - include explanation + practical implication
    - be written clearly and concisely

    Return ONLY a JSON list like:

    [
    {{"content": "...", "topic": "..."}},
    ...
    ]

    Text:
    {text}
    """

    all_chunks = []

    for doc in clean_docs:
        response = llm.invoke(CONDENSE_PROMPT.format(text=doc["text"]))
        
        raw = response.content
        
        # extract JSON safely
        match = re.search(r'(\[.*\])', raw, re.DOTALL)
        chunks = json.loads(match.group(1))
        
        # attach metadata
        for c in chunks:
            c["source"] = doc["source"]
            all_chunks.append(c)


    # Convert to documents
    documents = [
        Document(
            page_content=chunk["content"],
            metadata={
                "source": chunk["source"],
                "topic": chunk.get("topic", "general")
            }
        )
        for chunk in all_chunks
    ]

    # Create embeddings and vector DB (using Chroma)

    embeddings = OpenAIEmbeddings()

    vectorstore = Chroma.from_documents(
        documents,
        embedding=embeddings,
        persist_directory=DB_PATH # persist saves it
    )



# # Load later:
# if False:
#     vectorstore = Chroma(
#         persist_directory="./chroma_db",
#         embedding_function=embeddings
#     )


# def retrieve_knowledge(vectorstore, query: str, k: int = 3):
#     results = vectorstore.similarity_search(query, k=k)
    
#     return "\n\n".join([
#         f"{r.page_content} (source: {r.metadata['source']})"
#         for r in results
#     ])


# from langchain_core.tools import tool

# @tool
# def retrieve_coaching_knowledge(query: str) -> str:
#     """Retrieve relevant running coaching knowledge."""
#     return retrieve_knowledge(query)