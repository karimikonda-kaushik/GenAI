import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, os.getenv("SERVICE_ACCOUNT_FILE"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")

def add_spreadsheet_data(rows):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range=SHEET_NAME, valueInputOption="RAW", 
        body={"values": rows}
    ).execute()
    return result


add_spreadsheet_data([['Lebron James', 'King@gmail.com', '23'], 
    ['Kevin Durant', 'kd23@gmail.com', '35'],
    ['Kyrie Irving', 'kyrie@gmail.com', '27']])
