from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

from gmail_mcp_server import get_gmail_service

def init_auth():
    service = get_gmail_service()
    print("Auth successful")

if __name__ == "__main__":
    init_auth()