"""Interactive local OAuth authorization script for Gmail API.

Run this script locally to authorize access to your support Gmail account.
It prompts for client_secrets.json (or reads credentials.json), launches a local browser
flow, and outputs the resulting GOOGLE_REFRESH_TOKEN to copy into your .env file.
"""

import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Error: google-auth-oauthlib is required. Run 'uv sync' first.")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def main():
    credentials_path = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    if not os.path.exists(credentials_path):
        print(f"Error: {credentials_path} not found.")
        print(
            "Please download your OAuth client credentials from Google Cloud Console as 'credentials.json'"
        )
        print("and place it in the root directory (do not commit it to Git).")
        sys.exit(1)

    print("Starting Google OAuth 2.0 flow for Gmail API...")
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    if not creds.refresh_token:
        print(
            "\nWarning: No refresh token was returned. Google only returns a refresh token on the first consent"
        )
        print(
            "or when prompt='consent' is specified. Re-run or revoke authorization in your Google account."
        )
    else:
        print("\n=======================================================")
        print("Authorization successful!")
        print("Add the following lines to your .env file:")
        print(f"GOOGLE_CLIENT_ID={creds.client_id}")
        print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
        print("=======================================================\n")


if __name__ == "__main__":
    main()
