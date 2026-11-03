import os

import httpx
from google.oauth2.credentials import Credentials

JUNCTION_URL = os.getenv(
    "JUNCTION_URL",
    "http://127.0.0.1:8080"
).rstrip("/")


def get_google_credentials() -> Credentials:
    api_key = os.environ["API_KEY"]

    response = httpx.post(
        f"{JUNCTION_URL}/googleauth/internal/token",
        headers={
            "Authorization": f"Bearer {api_key}"
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()["data"]

    return Credentials(token=data["access_token"])