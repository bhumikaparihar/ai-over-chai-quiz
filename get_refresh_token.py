"""
One-time helper — run this locally, NOT as part of the deployed app.

Generates an OAuth refresh token for the AI Over Chai quiz's Google Sheets
connection. This does NOT create or download a service-account key, so it
works even when your Google Cloud organization enforces the
`iam.disableServiceAccountKeyCreation` policy — an OAuth client ID is a
different kind of credential, unaffected by that policy.

What it does:
  1. Opens your browser to a normal Google sign-in / consent screen.
  2. You sign in as the Google account that has (or will have) Editor
     access to the "AI Over Chai Quiz Responses" spreadsheet.
  3. Prints a ready-to-paste [gcp_oauth_credentials] block for
     .streamlit/secrets.toml.

Before running:
  - Complete Step 4.5 and 4.6 in the setup guide (OAuth consent screen +
    OAuth client ID, "Desktop app" type) and download that client's JSON.
  - Save the downloaded JSON next to this script as: oauth_client.json
  - Install the one extra package this script needs (not part of the
    deployed app's requirements.txt):

        pip install google-auth-oauthlib

Run:
        python get_refresh_token.py

This script and oauth_client.json are for local, one-time use only —
never commit either to a shared or public repository.
"""

import json
import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print(
        "Missing dependency. Run:\n\n    pip install google-auth-oauthlib\n",
        file=sys.stderr,
    )
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CLIENT_SECRETS_FILE = "oauth_client.json"


def main():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(
            f"Could not find {CLIENT_SECRETS_FILE} in this folder.\n"
            "Download it from Google Cloud Console (Credentials → your "
            "Desktop-app OAuth client → Download JSON) and save it here "
            f"as {CLIENT_SECRETS_FILE}.",
            file=sys.stderr,
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    # access_type="offline" + prompt="consent" guarantees a refresh token is
    # issued even if this Google account has authorized this app before.
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    if not credentials.refresh_token:
        print(
            "No refresh token was returned. Revoke this app's access at "
            "https://myaccount.google.com/permissions and run this script "
            "again.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nSuccess! Add this block to .streamlit/secrets.toml "
          "(replacing any existing [gcp_oauth_credentials] section):\n")
    print("[gcp_oauth_credentials]")
    print(f'client_id = "{credentials.client_id}"')
    print(f'client_secret = "{credentials.client_secret}"')
    print(f'refresh_token = "{credentials.refresh_token}"')
    print('token_uri = "https://oauth2.googleapis.com/token"')
    print(
        "\nKeep this output private — it is equivalent to a password for "
        "this Google account's Sheets/Drive access. Do not paste it into "
        "chat, commit it, or share it."
    )


if __name__ == "__main__":
    main()