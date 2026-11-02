import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials

# load this service's config
SERVICE_DIR = Path(__file__).resolve().parent
load_dotenv(SERVICE_DIR / ".env")

# import the shared Junction service config
SHARED_DIR = SERVICE_DIR.parent / "_shared"
sys.path.insert(0, str(SHARED_DIR))

from service_config import ServiceConfig

# request a valid Google access token from googleauth service
# the refresh token remains inside googleauth service
def get_google_credentials() -> Credentials:
    service_key = os.getenv("GOOGLEAUTH_CALENDAR_SERVICE_KEY")

    if not service_key:
        raise RuntimeError(
            "Missing GOOGLEAUTH_CALENDAR_SERVICE_KEY"
        )

    # url for googleauth service
    auth_url = ServiceConfig.get_url("googleauth")

    # ask googleauth for the token
    response = httpx.post(
        f"{auth_url}/internal/token",
        headers={
            "X-Googleauth-Service-Key": service_key
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()["data"]

    return Credentials(
        token=data["access_token"]
    )