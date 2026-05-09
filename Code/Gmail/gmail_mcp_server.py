import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP
import sys
import json

# Scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Get directory where this script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(BASE_DIR)
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

mcp = FastMCP("Gmail-Helper")

def get_gmail_service():
    """Authenticate and return Gmail service."""
    creds = None

    if not os.path.exists(TOKEN_FILE):
        raise Exception("Run auth setup first to generate token.json")
    # Load existing token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE , SCOPES)

    if creds and creds.expired:
        print("Token expired")

        if creds.refresh_token:
            try:
                print("🔄 Attempting refresh...")
                creds.refresh(Request())
                print("✅ Refresh successful")
            except Exception as e:
                print("❌ Refresh FAILED:", e)
                raise e   # 👈 IMPORTANT (stop fallback)

    # Refresh or create new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next time
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email via Gmail.
    :param to: Recipient email address
    :param subject: Email subject
    :param body: Email body text
    """
    try:
        service = get_gmail_service()

        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        raw = base64.urlsafe_b64encode(
            message.as_bytes()).decode('utf-8')

        result = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()

        return f"Email sent successfully! Message ID: {result['id']}"

    except Exception as e:
        return f"Failed to send email: {str(e)}"


@mcp.tool()
def search_emails(query: str, max_results: int = 5) -> str:
    """
    Search emails in Gmail.
    :param query: Search query (e.g. 'subject:support is:unread')
    :param max_results: Maximum number of emails to return
    """
    try:
        service = get_gmail_service()

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return "No emails found matching the query."

        email_list = []
        for msg in messages:
            detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            headers = {h['name']: h['value']
                      for h in detail['payload']['headers']}

            email_list.append(
                f"ID: {msg['id']}\n"
                f"From: {headers.get('From', 'Unknown')}\n"
                f"Subject: {headers.get('Subject', 'No subject')}\n"
                f"Date: {headers.get('Date', 'Unknown')}"
            )

        return "\n\n---\n\n".join(email_list)

    except Exception as e:
        return f"Failed to search emails: {str(e)}"


@mcp.tool()
def get_email_content(message_id: str) -> str:
    """
    Get full content of a specific email.
    :param message_id: Gmail message ID
    """
    try:
        service = get_gmail_service()

        detail = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = {h['name']: h['value']
                  for h in detail['payload']['headers']}

        # Extract body
        def extract_body(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part['mimeType'] == 'text/html':
                        data = part['body'].get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                data = payload.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')

            return ""

        body = extract_body(detail['payload'])

        return json.dumps({
            "id": message_id,
            "from": headers.get("From", "Unknown"),
            "subject": headers.get("Subject", "No subject"),
            "date": headers.get("Date", ""),
            "body": body[:2000]
        })


    except Exception as e:
        return f"Failed to get email: {str(e)}"
    

@mcp.tool()
def get_emails(query: str = "is:unread", max_results: int = 1) -> list:
    """
    Fetch list of email IDs + metadata
    """
    try:
        service = get_gmail_service()

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        return [
            {
                "id": msg["id"]
            }
            for msg in messages
        ]

    except Exception as e:
        return [{"error": str(e)}]
    

@mcp.tool()
def mark_as_read(message_id: str):
    service = get_gmail_service()

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

    return {"status": "marked_as_read", "id": message_id}


if __name__ == "__main__":
    print("Gmail MCP Server starting...", file=sys.stderr)
    mcp.run(transport="streamable-http")
    print("Gmail MCP Server started!", file=sys.stderr)