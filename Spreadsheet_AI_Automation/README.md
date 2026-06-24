# Spreadsheet AI Automation

Read Google Sheets data, detect new rows, summarize with Gemini, and email the summary.

## Prerequisites

- Python 3.9+
- Google Cloud project with **Google Sheets API** and **Gemini API** enabled
- Gmail account with an **App Password** (for sending email)
- Service account JSON key file in this folder

## Setup

```bash
cd /Users/kaushikkarimikonda/Documents/GenAI
source .venv/bin/activate
pip install -r Spreadsheet_AI_Automation/requirements.txt
```

## `.env` variables

Create or edit `.env` in this folder:

| Variable | Purpose |
|----------|---------|
| `SPREADSHEET_ID` | Google Sheet ID (from the sheet URL) |
| `SHEET_NAME` | Tab name (e.g. `Sheet1`) |
| `GOOGLE_API_KEY` | Google Sheets API (read via API key in `main.py`) |
| `GEMINI_API_KEY` | Gemini model for summaries |
| `SENDER_EMAIL` | Gmail address you send from |
| `SENDER_PASSWORD` | Gmail **App Password** (not your normal password) |
| `RECIPIENT_EMAIL` | Who receives the summary email |
| `SERVICE_ACCOUNT_FILE` | Filename of JSON key (e.g. `poetic-tube-498914-f5-b56e1c9d58c2.json`) |

Example `.env`:

```env
SPREADSHEET_ID=your_spreadsheet_id
SHEET_NAME=Sheet1
GOOGLE_API_KEY=your_google_api_key
GEMINI_API_KEY=your_gemini_api_key
SENDER_EMAIL=you@gmail.com
SENDER_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient@gmail.com
SERVICE_ACCOUNT_FILE=your-service-account.json
```

### Service account setup

1. [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create a **Service Account** → download JSON key → save in this folder
3. **Share your Google Sheet** with the service account email (Editor or Viewer)
4. Set `SERVICE_ACCOUNT_FILE` to the JSON filename only (script resolves the full path)

### Gmail app password

1. Google Account → Security → 2-Step Verification → App passwords
2. Generate a password for "Mail"
3. Put it in `SENDER_PASSWORD`

## Packages (`requirements.txt`)

- `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- `langchain`, `langchain-google-genai`, `python-dotenv`

## How to run

### Main automation (read sheet → AI summary → email)

```bash
cd Spreadsheet_AI_Automation
source ../.venv/bin/activate
python main.py
```

Tracks new rows in `last_row.txt` (created automatically, starts at `0`).

### Sheet utilities (service account)

```bash
python view_rows.py    # read all rows
python add_rows.py     # append rows
python edit_rows.py      # update a row by number
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `FileNotFoundError: last_row.txt` | Run from this folder, or use scripts with `BASE_DIR` paths |
| `FileNotFoundError: service account json` | Check `SERVICE_ACCOUNT_FILE` name matches the file in this folder |
| `403` Gemini API disabled | Enable [Generative Language API](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com) |
| Email fails | Use Gmail App Password; enable "less secure" is not enough — use App Password |
