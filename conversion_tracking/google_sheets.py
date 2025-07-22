import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "sheets-service-account-key.json"

credentials = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES,
)

client = gspread.authorize(credentials)

def push_to_sheet(sheet_id: str, row_data: list):
    sheet = client.open_by_key(sheet_id).sheet1
    existing = sheet.get_all_values()
    gclids = {row[0] for row in existing[1:]}  # başlık satırını atla
    if row_data[0] in gclids:
        return  # Aynı gclid varsa yazma
    sheet.append_row(row_data, value_input_option="USER_ENTERED")
