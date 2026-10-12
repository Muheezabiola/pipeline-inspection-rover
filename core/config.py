"""Load secrets and endpoints from the environment.

Values are read from a local ``.env`` file (never committed) with support for
real environment variables when running under a service manager.
"""

import os

from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
TARGET_EMAIL = os.getenv("TARGET_EMAIL")
API_COMMAND_URL = os.getenv("API_COMMAND_URL")
