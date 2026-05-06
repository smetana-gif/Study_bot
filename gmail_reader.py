import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [ #bot premissions
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

def get_google_service(service_name, version): #Checks if token.json exists
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build(service_name, version, credentials=creds)


def get_email_body(service, msg_id):
    msg = service.users().messages().get(
        userId='me',
        id=msg_id,
        format='full'
    ).execute()

    body = ''
    payload = msg['payload']

    if 'data' in payload.get('body', {}):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

    elif 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part.get('body', {}):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break

    return body


def get_emails(max_results=10):
    service = get_google_service('gmail', 'v1')

    query = 'subject:(מטלה OR assignment OR הגשה) from:(moodle.bgu.ac.il OR bgu.ac.il) newer_than:30d'

    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['Subject', 'From', 'Date']
        ).execute()

        headers = msg_data['payload']['headers']
        email_info = {
            'id': msg['id'],
            'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
            'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
            'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown'),
        }

        email_info['body'] = get_email_body(service, msg['id'])
        emails.append(email_info)
        print(f"📧 {email_info['date']} | {email_info['subject']}")

    return emails


if __name__ == '__main__':
    print("מתחבר ל־Gmail...")
    emails = get_emails()
    print(f"\nנמצאו {len(emails)} מיילים רלוונטיים")
    if emails:
        print("\n--- גוף המייל הראשון ---")
        print(emails[0]['body'][:500])