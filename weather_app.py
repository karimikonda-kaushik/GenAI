# Building a Weather AI Agent

import logging
import os
import warnings

# Suppress library warnings so the terminal shows only your app's output
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"
logging.basicConfig(level=logging.ERROR)
for _logger in ("urllib3", "google", "langchain", "langgraph"):
    logging.getLogger(_logger).setLevel(logging.ERROR)

import requests
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from langgraph.prebuilt import create_react_agent

load_dotenv()


@tool
def get_weather(city: str) -> str:
    """Get current weather for a given city or location 
    return temperatue in Fahrenheit label(e.g. 'Newark,NJ,US' or 'London,UK')."""
    api_key = os.getenv("OPENWEATHER_API_KEY") or os.getenv("OPENWEATHER_APT_KEY")
    if not api_key:
        return "Error: OPENWEATHER_API_KEY is not set in .env"

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}

    response = requests.get(base_url, params=params)
    data = response.json()
    temperature_celsius = data['main']['temp']
    temperature_fahrenheit = (temperature_celsius * 9/5) + 32
    return data, {'temperature_fahrenheit': temperature_fahrenheit} 



def get_location() -> str:
    """Get user's current location. Use when the user asks about weather without specifying a city."""
    response = requests.get("https://ipapi.co/json/", headers ={'User-agent': 'your-bot 0.1'})
    data = response.json()
    city = data.get('city')
    country = data.get('Country_name')
    return f'{city}, {country}'

system_prompt = """
You are a helpful weather assistant.
Your workflow:
1. If the user asks about weather WITHOUT specifying a location, you MUST:
   - First call get_location() to find their location
   - Then call get_weather(city) with that location

2. If the user provides a city or state, call get_weather with a specific query the API can resolve
   (e.g. for "New Jersey" use "Trenton,NJ,US" or "Newark,NJ,US", not just "New Jersey").

3. Use your Knowledge to determine which temperature unit is standard for given location.

4. present the weather information including, condition, wind speed, and any other relevant details.
"""

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

agent = create_react_agent(
    llm,
    tools=[get_weather, get_location],
    prompt=system_prompt,
    checkpointer=InMemorySaver(),
)

if __name__ == "__main__":
    while True:
            
        config = {"configurable": {"thread_id": "1"}}
        user_query = input("enter your query: ")
        if user_query in ["exit", "quit", "bye"]:
            break

        response = agent.invoke(
            {"messages": [HumanMessage(content=user_query)]},
            config,
        )
        print(response["messages"][-1].content)
