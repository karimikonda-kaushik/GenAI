# Recipe Generator

Upload a food image and get Indian recipe suggestions using Gemini or OpenAI.

## Prerequisites

- Python 3.9+ (uses shared venv at `../.venv`)
- Gemini API enabled on your Google Cloud project

## Setup

```bash
cd /Users/kaushikkarimikonda/Documents/GenAI
source .venv/bin/activate
pip install -r Recipe_generator/requirements.txt
```

## `.env` variables

Create or edit `.env` in this folder:

| Variable | Required for | Where to get it |
|----------|--------------|-----------------|
| `GOOGLE_API_KEY` | Gemini scripts & Gradio app | [Google AI Studio](https://aistudio.google.com/apikey) |
| `OPENAI_API_KEY` | `text_query_openai.py` (optional) | [OpenAI Platform](https://platform.openai.com/api-keys) |

Example `.env`:

```env
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Packages (`requirements.txt`)

- `langchain`, `langchain-google-genai`, `langchain-openai`
- `python-dotenv`
- `gradio`, `huggingface_hub<1.0`, `pydantic==2.10.6`

> **Note:** Pinned versions are for Python 3.9 compatibility. Langchain 1.x requires Python 3.10+.

## How to run

### Gradio web app (recommended)

```bash
cd Recipe_generator
source ../.venv/bin/activate
python gradio_app.py
```

Open **http://127.0.0.1:7860** in your browser.

**Auto-reload while coding** (restarts on save):

```bash
gradio gradio_app.py
```

### Terminal scripts

```bash
# Gemini — text or image
python text_query_gemini.py

# Gemini — recipe from ingredients image
python text_query_gemini2.py

# OpenAI — image (needs billing on OpenAI account)
python text_query_openai.py
```

Place test images in `images/` (e.g. `images/img.png`, `images/ingredients.png`).

## Troubleshooting

| Error | Fix |
|-------|-----|
| `429` / quota exceeded (Gemini) | Wait ~1 minute; free tier is 5 req/min for some models |
| `insufficient_quota` (OpenAI) | Add billing at platform.openai.com |
| `flagging_mode` error | Use `allow_flagging="never"` (Gradio 4.44) |
| Wrong API key loaded | Scripts load `.env` from this folder — run from here or use `BASE_DIR` paths |
