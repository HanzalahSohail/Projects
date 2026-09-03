"""
CRM Tools: create_lead, log_call_summary

Uses local JSON file storage for the demo.
In production, connect to Salesforce / HubSpot / etc.
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from tools import Tool, registry

# Storage directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LEADS_FILE = DATA_DIR / "leads.json"
CALL_LOGS_FILE = DATA_DIR / "call_logs.json"


def _load_json(filepath: Path) -> list:
    if filepath.exists():
        return json.loads(filepath.read_text())
    return []


def _save_json(filepath: Path, data: list):
    filepath.write_text(json.dumps(data, indent=2, default=str))


# ─── Create Lead ─────────────────────────────────────────────────────────────

async def _create_lead(name: str, phone: str = "", email: str = "",
                       company: str = "", notes: str = "") -> dict:
    """Create a new lead/contact record."""

    leads = _load_json(LEADS_FILE)

    lead = {
        "id": len(leads) + 1,
        "name": name,
        "phone": phone,
        "email": email,
        "company": company,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "status": "new"
    }

    leads.append(lead)
    _save_json(LEADS_FILE, leads)

    print(f"[CRM] Created lead #{lead['id']}: {name}")
    return {"status": "created", "lead_id": lead["id"], "name": name}


create_lead_tool = Tool(
    name="create_lead",
    description="Create a new lead or contact record in the CRM. Use when the user wants to save contact information, create a lead, or add a new customer.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Full name of the lead/contact"
            },
            "phone": {
                "type": "string",
                "description": "Phone number (optional)"
            },
            "email": {
                "type": "string",
                "description": "Email address (optional)"
            },
            "company": {
                "type": "string",
                "description": "Company name (optional)"
            },
            "notes": {
                "type": "string",
                "description": "Additional notes about the lead (optional)"
            }
        },
        "required": ["name"]
    },
    execute_fn=_create_lead,
    retries=1,
    timeout=10.0
)


# ─── Log Call Summary ────────────────────────────────────────────────────────

async def _log_call_summary(caller_name: str, summary: str,
                             duration_seconds: int = 0,
                             outcome: str = "completed",
                             follow_up: str = "") -> dict:
    """Log a call summary."""

    logs = _load_json(CALL_LOGS_FILE)

    log_entry = {
        "id": len(logs) + 1,
        "caller_name": caller_name,
        "summary": summary,
        "duration_seconds": duration_seconds,
        "outcome": outcome,
        "follow_up": follow_up,
        "logged_at": datetime.now().isoformat()
    }

    logs.append(log_entry)
    _save_json(CALL_LOGS_FILE, logs)

    print(f"[CRM] Logged call #{log_entry['id']}: {caller_name}")
    return {"status": "logged", "log_id": log_entry["id"], "caller": caller_name}


log_call_summary_tool = Tool(
    name="log_call_summary",
    description="Log a summary of a phone call or conversation. Use when the user asks to log, record, or save a call summary or meeting notes.",
    parameters={
        "type": "object",
        "properties": {
            "caller_name": {
                "type": "string",
                "description": "Name of the caller or participant"
            },
            "summary": {
                "type": "string",
                "description": "Summary of the call/conversation"
            },
            "duration_seconds": {
                "type": "integer",
                "description": "Call duration in seconds (optional)"
            },
            "outcome": {
                "type": "string",
                "enum": ["completed", "no_answer", "voicemail", "callback_requested", "escalated"],
                "description": "Outcome of the call"
            },
            "follow_up": {
                "type": "string",
                "description": "Any follow-up action needed (optional)"
            }
        },
        "required": ["caller_name", "summary"]
    },
    execute_fn=_log_call_summary,
    retries=1,
    timeout=10.0
)


# ─── Register All ────────────────────────────────────────────────────────────

def register_crm_tools():
    registry.register(create_lead_tool)
    registry.register(log_call_summary_tool)
    print("[TOOLS] CRM tools registered: create_lead, log_call_summary")