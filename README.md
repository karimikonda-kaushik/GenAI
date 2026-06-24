# GenAI (root project)

This folder contains shared experiments: Gemini chat, weather agent, and Flask chat app.

## Prerequisites

- Python 3.9+ (3.10+ recommended)
- Virtual environment at `GenAI/.venv` (shared across sub-projects)

## Setup

```bash
cd /Users/kaushikkarimikonda/Documents/GenAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## `.env` variables

Create or edit `.env` in this folder:

| Variable | Required for | Where to get it |
|----------|--------------|-----------------|
| `GOOGLE_API_KEY` | Gemini / LangChain scripts | [Google AI Studio](https://aistudio.google.com/apikey) — enable **Gemini API** |
| `OPENWEATHER_API_KEY` | Weather tools / web app | [OpenWeather](https://openweathermap.org/api) |
| `SUPABASE_DB_URI` | `weather_r_main.py` (Postgres memory) | [Supabase](https://supabase.com) → Project Settings → Database → connection string |

Optional for Flask app (`app.py`):

| Variable | Purpose |
|----------|---------|
| `FLASK_SECRET_KEY` | Session security (defaults to a dev value if unset) |

Example `.env`:

```env
GOOGLE_API_KEY=your_google_api_key
OPENWEATHER_API_KEY=your_openweather_key
SUPABASE_DB_URI=postgresql://user:password@host:port/db?sslmode=require
```

## How to run

### Simple Gemini chat (`first_main.py`)

```bash
source .venv/bin/activate
python first_main.py
```

Requires `GOOGLE_API_KEY` and `cars.txt` in this folder.

### Weather agent with memory (`weather_r_main.py`)

```bash
source .venv/bin/activate
python weather_r_main.py
```

Requires `GOOGLE_API_KEY` and `SUPABASE_DB_URI`.

### Weather Flask web chat (`app.py`)

```bash
source .venv/bin/activate
python app.py
```

Open the URL shown in the terminal (usually `http://127.0.0.1:5000`).

Requires `GOOGLE_API_KEY` and `OPENWEATHER_API_KEY` (used by `weatherwebapp.py`).

## Notes

- `.env` is git-ignored — never commit API keys.
- Sub-projects (`Recipe_generator/`, `Spreadsheet_AI_Automation/`) have their own `.env` and README files.
