"""
Scheduling tools — powered by your Cal.com MCP client.

Fixes:
  1. Timezone: get_availability now passes timezone to Cal.com so slots are
     returned in Asia/Karachi time, not UTC.
  2. Cancel all: added get_bookings_for_date tool so the LLM can fetch all
     booking UIDs for a date, then cancel each one individually.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CAL_API_KEY         = os.getenv("CAL_API_KEY", "")
CAL_USERNAME        = os.getenv("CAL_USERNAME", "")
CAL_EVENT_TYPE_SLUG = os.getenv("CAL_EVENT_TYPE_SLUG", "30min")
CAL_EVENT_TYPE_ID   = os.getenv("CAL_EVENT_TYPE_ID", "")
CAL_TIMEZONE        = os.getenv("CAL_TIMEZONE", "Asia/Karachi")

import sys
import os as _os

_here = _os.path.dirname(_os.path.abspath(__file__))
for _candidate in [
    _os.path.join(_here, ".."),
    _os.path.join(_here, "..", ".."),
    _os.path.join(_here, "..", "cal-mcp"),
]:
    _candidate = _os.path.abspath(_candidate)
    if _os.path.isdir(_os.path.join(_candidate, "cal_mcp")):
        sys.path.insert(0, _candidate)
        logger.info(f"[SCHEDULING] Found cal_mcp at: {_candidate}")
        break

try:
    from cal_mcp.client import (
        get_availability as _cal_get_availability,
        get_bookings     as _cal_get_bookings,
        create_booking   as _cal_create_booking,
        cancel_booking   as _cal_cancel_booking,
    )
    CAL_CLIENT_AVAILABLE = True
    logger.info("[SCHEDULING] Cal.com client imported successfully")
except ImportError as e:
    CAL_CLIENT_AVAILABLE = False
    logger.warning(f"[SCHEDULING] cal_mcp not found ({e}) — using mock mode")


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_slots(date: str) -> dict:
    base = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    slots = []
    for hour in [9, 10, 11, 14, 15, 16]:
        t = base.replace(hour=hour, minute=0, second=0)
        slots.append(t.strftime("%Y-%m-%dT%H:%M:%S") + "+05:00")
    return {
        "status": "mock",
        "date": date,
        "timezone": CAL_TIMEZONE,
        "slots": slots,
        "note": "Mock data — connect Cal.com for real availability"
    }


def _mock_bookings(date: str) -> dict:
    return {
        "status": "mock",
        "date": date,
        "bookings": [
            {"uid": "mock-uid-1", "title": "Mock Meeting 1", "start": f"{date}T09:00:00+05:00"},
            {"uid": "mock-uid-2", "title": "Mock Meeting 2", "start": f"{date}T11:00:00+05:00"},
        ],
        "note": "Mock data — connect Cal.com for real bookings"
    }


def _mock_booking(name: str, email: str, start_time: str) -> dict:
    return {
        "status": "mock_booked",
        "uid": f"mock-{abs(hash(email)) % 100000}",
        "name": name,
        "email": email,
        "start": start_time,
        "note": "Mock booking — connect Cal.com for real bookings"
    }


def _mock_cancel(booking_id: str) -> dict:
    return {
        "status": "mock_cancelled",
        "uid": booking_id,
        "note": "Mock cancellation — connect Cal.com for real cancellations"
    }


# ── Tool implementations ──────────────────────────────────────────────────────

async def _get_availability(date: str, timezone: str = None) -> dict:
    """
    Get available meeting slots for a given date.
    FIX: timezone is now passed to Cal.com so slots reflect local time correctly.
    """
    tz = timezone or CAL_TIMEZONE

    if not CAL_CLIENT_AVAILABLE or not CAL_API_KEY or not CAL_USERNAME:
        logger.info("[get_availability] Using mock mode")
        return _mock_slots(date)

    try:
        start_dt  = datetime.strptime(date, "%Y-%m-%d")
        end_dt    = start_dt + timedelta(days=1)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str   = end_dt.strftime("%Y-%m-%d")

        logger.info(f"[get_availability] user={CAL_USERNAME} slug={CAL_EVENT_TYPE_SLUG} {start_str}→{end_str} tz={tz}")

        result = await _cal_get_availability(
            username=CAL_USERNAME,
            event_type_slug=CAL_EVENT_TYPE_SLUG,
            start=start_str,
            end=end_str,
            timezone=tz,          # ← FIX: pass timezone through
        )

        if result.get("error"):
            logger.warning(f"[get_availability] Cal.com error: {result}")
            return _mock_slots(date)

        raw_slots = result.get("data", {})
        flat = []
        for day_slots in raw_slots.values():
            for slot in day_slots:
                flat.append(slot.get("time", slot) if isinstance(slot, dict) else slot)

        return {
            "status": "success",
            "date": date,
            "timezone": tz,
            "slots": flat,
        }

    except Exception as e:
        logger.exception(f"[get_availability] Error: {e}")
        return _mock_slots(date)


async def _get_bookings_for_date(date: str) -> dict:
    """
    NEW: Fetch all bookings for a specific date.
    Returns a list of bookings with uid, title, and start time.
    The LLM uses this before 'cancel all' to know which UIDs to cancel.
    """
    if not CAL_CLIENT_AVAILABLE or not CAL_API_KEY:
        logger.info("[get_bookings_for_date] Using mock mode")
        return _mock_bookings(date)

    try:
        # date_from = start of that day, date_to = start of next day
        start_dt = datetime.strptime(date, "%Y-%m-%d")
        end_dt   = start_dt + timedelta(days=1)

        result = await _cal_get_bookings(
            date_from=start_dt.strftime("%Y-%m-%dT00:00:00Z"),
            date_to=end_dt.strftime("%Y-%m-%dT00:00:00Z"),
            status="upcoming"
        )

        if result.get("error"):
            logger.warning(f"[get_bookings_for_date] Cal.com error: {result}")
            return _mock_bookings(date)

        # Extract just what the LLM needs: uid + start time + title
        raw = result.get("data", {}).get("bookings", [])
        bookings = []
        for b in raw:
            bookings.append({
                "uid":   b.get("uid"),
                "title": b.get("title", "Meeting"),
                "start": b.get("start"),
            })

        logger.info(f"[get_bookings_for_date] {len(bookings)} bookings found for {date}")
        return {
            "status": "success",
            "date": date,
            "count": len(bookings),
            "bookings": bookings,
        }

    except Exception as e:
        logger.exception(f"[get_bookings_for_date] Error: {e}")
        return _mock_bookings(date)


async def _book_meeting(name: str, email: str, start_time: str,
                         timezone: str = None, notes: str = "") -> dict:
    tz = timezone or CAL_TIMEZONE

    if not CAL_CLIENT_AVAILABLE or not CAL_API_KEY or not CAL_EVENT_TYPE_ID:
        logger.info("[book_meeting] Using mock mode")
        return _mock_booking(name, email, start_time)

    try:
        if not start_time.endswith("Z"):
            start_time = start_time + "Z"

        booking_data = {
            "eventTypeId": int(CAL_EVENT_TYPE_ID),
            "start": start_time,
            "attendee": {
                "name": name,
                "email": email,
                "timeZone": tz,
            },
        }
        if notes:
            booking_data["metadata"] = {"notes": notes}

        logger.info(f"[book_meeting] {name} <{email}> at {start_time}")
        result = await _cal_create_booking(booking_data)

        if result.get("error"):
            logger.warning(f"[book_meeting] Cal.com error: {result}")
            return _mock_booking(name, email, start_time)

        uid = result.get("data", {}).get("uid", "unknown")
        logger.info(f"[book_meeting] Booked — uid={uid}")
        return {
            "status": "booked",
            "uid": uid,
            "name": name,
            "email": email,
            "start": start_time,
        }

    except Exception as e:
        logger.exception(f"[book_meeting] Error: {e}")
        return _mock_booking(name, email, start_time)


async def _cancel_meeting(booking_id: str, reason: str = "Cancelled by agent") -> dict:
    if not CAL_CLIENT_AVAILABLE or not CAL_API_KEY:
        logger.info("[cancel_meeting] Using mock mode")
        return _mock_cancel(booking_id)

    try:
        logger.info(f"[cancel_meeting] uid={booking_id}")
        result = await _cal_cancel_booking(booking_id, reason)

        if result.get("error"):
            logger.warning(f"[cancel_meeting] Cal.com error: {result}")
            return _mock_cancel(booking_id)

        logger.info(f"[cancel_meeting] Cancelled — uid={booking_id}")
        return {
            "status": "cancelled",
            "uid": booking_id,
            "reason": reason,
        }

    except Exception as e:
        logger.exception(f"[cancel_meeting] Error: {e}")
        return _mock_cancel(booking_id)


# ── Registration ──────────────────────────────────────────────────────────────

def register_scheduling_tools():
    from tools import registry, Tool

    registry.register(Tool(
        name="get_availability",
        description=(
            "Get available meeting time slots for a specific date. "
            "Returns slots in Asia/Karachi local time. "
            "Always call this before booking so you know which slots are free."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format e.g. 2026-04-01"
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone override e.g. Asia/Karachi (optional, defaults to Asia/Karachi)"
                }
            },
            "required": ["date"]
        },
        execute_fn=_get_availability
    ))

    # NEW TOOL
    registry.register(Tool(
        name="get_bookings_for_date",
        description=(
            "Get all existing bookings for a specific date. "
            "Returns a list of bookings with their UIDs and start times. "
            "ALWAYS call this first when the user says 'cancel all meetings' or "
            "'cancel all bookings' — you need the UIDs before you can cancel anything."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format e.g. 2026-04-01"
                }
            },
            "required": ["date"]
        },
        execute_fn=_get_bookings_for_date
    ))

    registry.register(Tool(
        name="book_meeting",
        description=(
            "Book a meeting slot on Cal.com. "
            "start_time must be in UTC e.g. if user says 10am Karachi, use 05:00:00Z."
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name of the attendee"
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the attendee"
                },
                "start_time": {
                    "type": "string",
                    "description": "UTC start time in ISO 8601 format e.g. 2026-04-01T05:00:00Z"
                },
                "timezone": {
                    "type": "string",
                    "description": "Attendee timezone (optional, defaults to Asia/Karachi)"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes (optional)"
                }
            },
            "required": ["name", "email", "start_time"]
        },
        execute_fn=_book_meeting
    ))

    registry.register(Tool(
        name="cancel_meeting",
        description=(
            "Cancel a single meeting by its booking UID. "
            "To cancel multiple meetings, call this once per UID. "
            "If you don't have the UID, call get_bookings_for_date first."
        ),
        parameters={
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "The booking UID to cancel"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for cancellation (optional)"
                }
            },
            "required": ["booking_id"]
        },
        execute_fn=_cancel_meeting
    ))

    logger.info("[TOOLS] Scheduling tools registered: get_availability, get_bookings_for_date, book_meeting, cancel_meeting")