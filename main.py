from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

load_dotenv()


@tool
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return "condition: sunny, temperature: 25°C"


@tool
def get_location() -> str:
    """Get user's current location. Use when the user asks about weather without specifying a city."""
    return "Rome, Italy"


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

system_prompt = """
You are a helpful weather assistant.
YOUR WORKFLOW:
1. If the user asks about weather WITHOUT specifying a location, you MUST:
   - First call get_location() to find their location
   - Then call get_weather(city) with that location

2. If the user provides a city, call get_weather(city) directly.
"""

agent = create_react_agent(
    llm,
    tools=[get_weather, get_location],
    prompt=system_prompt,
)

user_query = input("Enter your query: ")

response = agent.invoke({"messages": [HumanMessage(content=user_query)]})
print(response["messages"][-1].content)
