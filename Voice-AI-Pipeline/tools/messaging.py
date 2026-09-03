"""
Messaging Tools: SMS (Twilio), WhatsApp (Twilio), Email (SMTP)
"""

import os
import asyncio
from dotenv import load_dotenv
from tools import Tool, registry

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────────

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_WA = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")


# ─── SMS ─────────────────────────────────────────────────────────────────────

async def _send_sms(to: str, message: str) -> dict:
    """Send SMS via Twilio."""
    if not TWILIO_SID or not TWILIO_TOKEN:
        return {"status": "error", "detail": "Twilio credentials not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env"}

    from twilio.rest import Client

    def _sync_send():
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=to
        )
        return {"status": "sent", "sid": msg.sid, "to": to}

    return await asyncio.get_event_loop().run_in_executor(None, _sync_send)


send_sms_tool = Tool(
    name="send_sms",
    description="Send an SMS text message to a phone number. Use when the user asks to send a text message or SMS.",
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Phone number in E.164 format, e.g. +14155551234"
            },
            "message": {
                "type": "string",
                "description": "The text message content to send"
            }
        },
        "required": ["to", "message"]
    },
    execute_fn=_send_sms,
    retries=2,
    timeout=15.0
)


# ─── WhatsApp ────────────────────────────────────────────────────────────────

async def _send_whatsapp(to: str, message: str) -> dict:
    """Send WhatsApp message via Twilio."""
    if not TWILIO_SID or not TWILIO_TOKEN:
        return {"status": "error", "detail": "Twilio credentials not configured"}

    from twilio.rest import Client

    def _sync_send():
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        # Ensure 'whatsapp:' prefix
        to_wa = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WA,
            to=to_wa
        )
        return {"status": "sent", "sid": msg.sid, "to": to_wa}

    return await asyncio.get_event_loop().run_in_executor(None, _sync_send)


send_whatsapp_tool = Tool(
    name="send_whatsapp",
    description="Send a WhatsApp message to a phone number. Use when the user asks to send a WhatsApp message.",
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Phone number in E.164 format, e.g. +14155551234"
            },
            "message": {
                "type": "string",
                "description": "The WhatsApp message content to send"
            }
        },
        "required": ["to", "message"]
    },
    execute_fn=_send_whatsapp,
    retries=2,
    timeout=15.0
)


# ─── Email ───────────────────────────────────────────────────────────────────

async def _send_email(to: str, subject: str, body: str) -> dict:
    """Send email via SMTP (Gmail)."""
    if not SMTP_USER or not SMTP_PASS:
        return {"status": "error", "detail": "SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env"}

    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    await aiosmtplib.send(
        msg,
        hostname=SMTP_HOST,
        port=SMTP_PORT,
        username=SMTP_USER,
        password=SMTP_PASS,
        start_tls=True,
    )

    return {"status": "sent", "to": to, "subject": subject}


send_email_tool = Tool(
    name="send_email",
    description="Send an email to an email address. Use when the user asks to send or compose an email.",
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address"
            },
            "subject": {
                "type": "string",
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Email body text"
            }
        },
        "required": ["to", "subject", "body"]
    },
    execute_fn=_send_email,
    retries=2,
    timeout=20.0
)


# ─── Register All ────────────────────────────────────────────────────────────

def register_messaging_tools():
    registry.register(send_sms_tool)
    registry.register(send_whatsapp_tool)
    registry.register(send_email_tool)
    print("[TOOLS] Messaging tools registered: send_sms, send_whatsapp, send_email")