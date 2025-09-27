import os
from pathlib import Path
import logging
import msal
import requests
from dotenv import load_dotenv
logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID")
GRAPH_AUTHORITY = os.getenv("GRAPH_AUTHORITY", "https://login.microsoftonline.com/common")
GRAPH_SCOPES = [
    scope.strip()
    for scope in os.getenv("GRAPH_SCOPES", "Mail.Send").replace(",", " ").split()
    if scope.strip()
]
GRAPH_DEFAULT_RECIPIENTS = [
    addr.strip()
    for addr in os.getenv("GRAPH_RECIPIENT_EMAILS", "").split(",")
    if addr.strip()
]
GRAPH_TOKEN_CACHE_PATH = Path(os.getenv("GRAPH_TOKEN_CACHE_PATH", "~/.pararius_graph_cache")).expanduser()

if not GRAPH_CLIENT_ID:
    raise RuntimeError("GRAPH_CLIENT_ID is not set in .env")
if not GRAPH_SCOPES:
    raise RuntimeError("GRAPH_SCOPES is empty; provide at least one delegated permission scope")


def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "disable_web_page_preview": False}
    try:
        requests.post(url, data=data, timeout=10).raise_for_status()
        return "Message sent successfully"
    except requests.RequestException as exc:
        return "Error sending Telegram message: %s" % exc


def _load_cache():
    cache = msal.SerializableTokenCache()
    if GRAPH_TOKEN_CACHE_PATH.exists():
        cache.deserialize(GRAPH_TOKEN_CACHE_PATH.read_text())
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        GRAPH_TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_TOKEN_CACHE_PATH.write_text(cache.serialize())


def _graph_token():
    cache = _load_cache()
    app = msal.PublicClientApplication(
        client_id=GRAPH_CLIENT_ID,
        authority=GRAPH_AUTHORITY,
        token_cache=cache,
    )

    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to initiate device flow: {flow}")
        logger.info("Authenticate with Microsoft by visiting %s and entering code %s", flow["verification_uri"], flow["user_code"])
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Token acquisition failed: {result.get('error_description', result)}")

    _save_cache(cache)
    return result["access_token"]


def send_email(recipients, subject, body, *, html=False, save_to_sent=False):
    if isinstance(recipients, str):
        recipients = [recipients]

    recipients = [addr for addr in recipients if addr]

    message_payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML" if html else "Text", "content": body},
            "toRecipients": [
                {"emailAddress": {"address": address}}
                for address in recipients
            ],
        },
        "saveToSentItems": save_to_sent,
    }

    token = _graph_token()
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, json=message_payload, headers=headers, timeout=10)
    try:
        logger.info(f"Email sent to {', '.join(recipients)}")
        response.raise_for_status()
        
    except requests.HTTPError as exc:
        logger.error(f"Error sending email: {exc}")
        raise