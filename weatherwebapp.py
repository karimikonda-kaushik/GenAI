# Weather agent shared by Flask app and CLI

import logging
import os
import sqlite3
import warnings

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR)

load_dotenv()


def _get_api_key():
    return os.getenv("OPENWEATHER_API_KEY") or os.getenv("OPENWEATHER_APT_KEY")


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city or location (e.g. 'Exton,PA,US' or '19425,US')."""
    api_key = _get_api_key()
    if not api_key:
        return "Error: OPENWEATHER_API_KEY is not set in .env"

    base_url = "https://api.openweathermap.org/data/2.5/weather"

    try:
        response = requests.get(
            base_url,
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=10,
        )
        data = response.json()

        if data.get("cod") != 200:
            # Fallback: use browser lat/lon from Flask session (more reliable)
            try:
                from flask import has_request_context, session

                if has_request_context() and session.get("user_location"):
                    lat = session["user_location"]["lat"]
                    lon = session["user_location"]["lon"]
                    response = requests.get(
                        base_url,
                        params={
                            "lat": lat,
                            "lon": lon,
                            "appid": api_key,
                            "units": "metric",
                        },
                        timeout=10,
                    )
                    data = response.json()
            except Exception:
                pass

        if data.get("cod") != 200:
            return f"Error: {data.get('message', 'city not found')} (tried: {city})"

        temp_c = data["main"]["temp"]
        temp_f = (temp_c * 9 / 5) + 32
        desc = data["weather"][0]["description"]
        name = data.get("name", city)
        wind = data.get("wind", {}).get("speed", "N/A")
        return (
            f"{name}: {desc}, {temp_c:.1f}°C ({temp_f:.1f}°F), "
            f"wind {wind} m/s"
        )
    except requests.RequestException as exc:
        return f"Error: could not reach weather API ({exc})"
    except (KeyError, TypeError) as exc:
        return f"Error: unexpected API response ({exc})"


@tool
def get_location() -> str:
    """Get user's current location from browser GPS. Use when no city is given."""
    try:
        from flask import has_request_context, session

        if not has_request_context() or not session.get("user_location"):
            return "Error: location not available — allow browser location access and send a message again"

        lat = session["user_location"]["lat"]
        lon = session["user_location"]["lon"]

        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "WeatherAssistant/1.0"},
            timeout=10,
        )
        data = response.json()
        addr = data.get("address", {})

        city = addr.get("city") or addr.get("town") or addr.get("village") or "Unknown"
        state = addr.get("state", "")
        postcode = addr.get("postcode", "")
        country = addr.get("country", "")

        # OpenWeather works better with zip or "City,ST,US" than township names
        if postcode and country == "United States":
            weather_query = f"{postcode},US"
        else:
            weather_query = f"{city},{state},US" if state else f"{city},{country}"

        session["weather_query"] = weather_query
        return f"{city}, {state}, {country} (use {weather_query} for weather lookup)"
    except Exception as exc:
        return f"Error: could not resolve location ({exc})"


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

system_prompt = """
You are a helpful weather assistant.
YOUR WORKFLOW:
1. If the user asks about weather WITHOUT a city, call get_location() first, then call get_weather with the lookup string it provides (e.g. 19425,US or Exton,PA,US).
2. If the user names a city, call get_weather(city) with a format like "City,ST,US".
3. Always use the exact string returned by get_location for the get_weather city argument when possible.
"""

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
checkpointer.setup()

agent = create_react_agent(
    llm,
    tools=[get_weather, get_location],
    prompt=system_prompt,
    checkpointer=checkpointer,
)
