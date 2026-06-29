# Image Generation (Gemini)

Generate images using Google's Gemini image models.

## Prerequisites

- Python 3.9+ (uses shared venv at `../.venv`)
- **Google API key** with Gemini API enabled

## Setup

```bash
cd /Users/kaushikkarimikonda/Documents/GenAI
source .venv/bin/activate
pip install python-dotenv google-genai
```

Or install from parent project if you already use LangChain:

```bash
pip install -r ../Recipe_generator/requirements.txt
```

## `.env` variables

Create or edit `.env` in this folder:

| Variable | Purpose | Where to get it |
|----------|---------|-----------------|
| `GOOGLE_API_KEY` | Gemini API access | [Google AI Studio](https://aistudio.google.com/apikey) |

Example `.env`:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

Copy from `.env.example` if starting fresh:

```bash
cp .env.example .env
```

Then paste your key after `=`.

## How to run

```bash
cd Img_gen
source ../.venv/bin/activate
python img_gen_gemi.py
```

Generated images are typically saved in this folder (e.g. `output/` or `images/`).

## Load API key in Python

```python
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

google_api_key = os.getenv("GOOGLE_API_KEY")
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `403` / API disabled | Enable [Generative Language API](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com) |
| `429` quota exceeded | Wait ~1 minute; check [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) |
| Key not found | Run from `Img_gen` or load `.env` with `BASE_DIR` path |

## Notes

- `.env` is git-ignored — never commit your API key.
- Parent directory: `GenAI/` — see root `README.md` for other projects.
