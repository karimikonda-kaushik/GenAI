# Building a Weather AI Agent

import logging
import warnings
import os

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR)

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

URI_DB = os.getenv("SUPABASE_DB_URI")
def get_weather(city: str):
    """Get weather for a given city."""
    return {"condition": "sunny", "temperature": 29}


def get_location():
    """Get user current location. Use when the user asks about weather without specifying a city."""
    return "Exton, Pennsylvania"


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

system_prompt = """
you area a helpful weather assistant
Your workflow:
1. If the user asks about weather WITHOUT specifying a location, you MUST:
   - First call get_location() to find their location
   - Then call get_weather(city) with that location

2. If the user provides a city, call get_weather(city) directly.
"""

if __name__ == "__main__":
    if not URI_DB:
        raise ValueError("SUPABASE_DB_URI is not set in .env")

    with PostgresSaver.from_conn_string(URI_DB) as checkpointer:
        checkpointer.setup()
        agent = create_react_agent(
            llm,
            tools=[get_weather, get_location],
            prompt=system_prompt,
            checkpointer=checkpointer,
        )

        config = {"configurable": {"thread_id": "1"}}

        while True:
            user_query = input("enter your query: ")
            if user_query in ["exit", "quit", "bye"]:
                break
            response = agent.invoke(
                {"messages": [HumanMessage(content=user_query)]},
                config,
            )
            print(response["messages"][-1].content)
