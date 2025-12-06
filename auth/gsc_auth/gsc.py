import os

from google_auth_oauthlib.flow import Flow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
REDIRECT_URI = "http://127.0.0.1:8000/auth/google/callback"


def create_flow():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    return flow
