import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, os.getenv("SERVICE_ACCOUNT_FILE"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")

def update_spreadsheet_data(rows, row_number):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    #Update a row
    # #range_name = f'{SHEET_NAME}!A{row_number}:C{row_number}'

    #Update a cell
    range_name = f'{SHEET_NAME}!A{row_number}'
    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=range_name, valueInputOption="RAW",
        body={"values": rows}
    ).execute()
    return result


result = update_spreadsheet_data([['Shaquille O\'Neal', 'shaq@gmail.com', '35']], 5)
print(result)
