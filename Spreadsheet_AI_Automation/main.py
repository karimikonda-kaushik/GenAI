from smtplib import SMTP_PORT
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LAST_ROW_FILE = os.path.join(BASE_DIR, "last_row.txt")

load_dotenv(os.path.join(BASE_DIR, ".env"))
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
SHEET_NAME = os.environ["SHEET_NAME"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def read_last_row():
    """Return last processed row index; default to 0 on first run."""
    if not os.path.exists(LAST_ROW_FILE):
        return 0
    content = open(LAST_ROW_FILE).read().strip()
    return int(content) if content else 0


def get_spreadsheet_data():
    """Fetch spreadsheet data"""
    service = build('sheets', 'v4', developerKey=GOOGLE_API_KEY)
    all_rows = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME
    ).execute()['values']
    last_row = read_last_row()
    new_rows = all_rows[last_row:]
    headers = all_rows[0]
    return all_rows, new_rows, headers

def summarize_with_ai(text):
    system_prompt = """
    you are a helpful assistant chat summarizer spreadsheet data
    you will receive new rows that were added to the google spreadsheet. please provide a clear, concis esummary of this data"""
    model = init_chat_model("gemini-2.5-flash", api_key=GEMINI_API_KEY, model_provider="google_genai")
    message = [{"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Here are the new rows from the spreadsheet \n {text}"}]

    response = model.invoke(message).content
    return response
    
def send_email(subject, body):
    """Send an email to the recipient"""
    message = MIMEMultipart()
    message['From'] = SENDER_EMAIL
    message['To'] = RECIPIENT_EMAIL
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(message)
    server.quit()
    return f"Email sent successfully to {RECIPIENT_EMAIL}"

all_rows, new_rows, headers = get_spreadsheet_data()
total_rows = len(all_rows)
with open(LAST_ROW_FILE, 'w') as file:
    file.write(str(total_rows))

message = f"Headers: {headers}\n New Rows: {new_rows}"
print(message)
summary = summarize_with_ai(message)

body = f"Here is todays summary \n\n{summary}\n\n Thanks!"
send_email('Daily spreadsheet summary', summary)

print("all rows: ", all_rows)
print("new rows: ", new_rows)
print(summary)