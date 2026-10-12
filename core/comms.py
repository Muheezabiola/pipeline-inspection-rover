"""Email alerting and backend API communication."""

import smtplib
from email.message import EmailMessage

import requests

from core.config import (
    API_COMMAND_URL,
    GMAIL_APP_PASSWORD,
    GMAIL_USER,
    TARGET_EMAIL,
)


def send_email_alert(subject, body):
    """Send an email alert using Gmail SMTP."""
    try:
        msg = EmailMessage()
        msg["From"] = GMAIL_USER
        msg["To"] = TARGET_EMAIL
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print("✅ Email alert sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def fetch_command():
    """Return the latest command from the backend, or None if unavailable."""
    response = requests.get(API_COMMAND_URL)
    if response.status_code == 200:
        return response.json().get("command")
    return None
