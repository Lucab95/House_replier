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

    # Improve email formatting to avoid spam filters
    if not html:
        # Convert plain text to basic HTML for better formatting
        body = body.replace('\n', '<br>\n')
        html = True

    # Extract URL from body to make it prominent
    import re
    url_match = re.search(r'URL:\s*(https?://[^\s\n]+)', body)
    primary_url = url_match.group(1) if url_match else ""
    
    # Structure the content for better readability
    formatted_body = body.replace('\n', '<br>\n')
    
    # Add proper email structure with anti-spam headers
    message_payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": f"""
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{subject}</title>
                    <meta property="og:title" content="{subject}">
                    <meta property="og:type" content="website">
                    {f'<meta property="og:url" content="{primary_url}">' if primary_url else ''}
                    <meta property="og:description" content="New housing listing notification">
                </head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                        <h2 style="color: #007bff; margin-top: 0;">🏠 Housing Alert Notification</h2>
                        
                        {f'''
                        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0; border: 1px solid #2196f3;">
                            <h3 style="margin: 0 0 10px 0; color: #1976d2;">📍 Primary Listing</h3>
                            <a href="{primary_url}" 
                               style="display: block; padding: 12px; background-color: #2196f3; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; text-align: center; margin: 10px 0;"
                               target="_blank">
                                🔗 View Property Listing
                            </a>
                            <p style="font-size: 11px; color: #666; margin: 5px 0 0 0; word-break: break-all;">
                                {primary_url}
                            </p>
                        </div>
                        ''' if primary_url else ''}
                        
                        <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 15px 0;">
                            <h4 style="margin-top: 0; color: #333;">📋 Listing Details</h4>
                            <div style="font-family: 'Courier New', monospace; font-size: 13px; line-height: 1.4;">
                                {formatted_body}
                            </div>
                        </div>
                        
                        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                        <p style="font-size: 12px; color: #6c757d; margin: 0;">
                            🤖 This is an automated notification from your housing monitoring system.<br>
                            📅 Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                </body>
                </html>
                """
            },
            "toRecipients": [
                {"emailAddress": {"address": address}}
                for address in recipients
            ],
            "from": {
                "emailAddress": {
                    "address": "luca.brugaletta@outlook.com",
                    "name": "Housing Monitor System"
                }
            },
            "importance": "normal",
            "internetMessageHeaders": [
                {
                    "name": "X-Auto-Response-Suppress",
                    "value": "All"
                },
                {
                    "name": "X-Priority",
                    "value": "3"
                },
                {
                    "name": "X-MSMail-Priority",
                    "value": "Normal"
                }
            ]
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
        response.raise_for_status()
        logger.info(f"Email sent to {', '.join(recipients)}")
        
    except requests.HTTPError as exc:
        logger.error(f"Error sending email: {exc}")
        raise