import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Paths
BASE_DIR = os.path.dirname(__file__)
CREDENTIALS_FILE = os.path.join(BASE_DIR, '..', 'credentials.json')  # OAuth client credentials
TOKEN_FILE = os.path.join(BASE_DIR, '..', 'token.pickle')  # Saved login token

# Folder in your personal Google Drive (or remove 'parents' to upload to root)
FOLDER_ID = '1nDv1pvz9WUHXc_dS2x0mTb4v_rODx524'


def get_service():
    creds = None

    # 1. Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # 2. If no valid token, run console-based OAuth (copy/paste flow)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("⚠️  No valid token found. Starting manual console login...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob"
            )

            # Always force manual copy/paste flow
            auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
            print(f"\n🔗 Please go to this URL in your browser:\n{auth_url}\n")
            code = input("👉 Paste the authorization code here: ")

            flow.fetch_token(code=code)
            creds = flow.credentials  # ✅ Properly get the credentials

        # Save the token for next time
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path):
    service = get_service()
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='application/zip')
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    return file


if __name__ == "__main__":
    backup_file = "/app/backups/full_backup.zip"  # You can replace with latest finder
    result = upload_to_drive(backup_file)
    print(f"✅ Uploaded: {result['webViewLink']}")