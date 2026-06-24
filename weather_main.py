#Building a Weather AI Agent

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

def get_weather(city: str):
    """Get weather for a given city."""
    #this is a form of string return "Sunny"
    #this is a form of dictionary
    return {'condition': 'sunny', 'temperature': 29}

def get_location():
    """Get user current location,  use this when user asks about weather """
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

agent = create_react_agent(
    llm,
    tools=[get_weather, get_location],
    prompt=system_prompt,
    checkpointer=InMemorySaver(),
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}

    user_query = input("enter your query: ")
    response1 = agent.invoke(
        {"messages": [HumanMessage(content=user_query)]},
        config,
    )
    print(response1["messages"][-1].content)

    user_query2 = input("enter your follow-up query: ")
    response2 = agent.invoke(
        {"messages": [HumanMessage(content=user_query2)]},
        config,
    )
    print(response2["messages"][-1].content) 