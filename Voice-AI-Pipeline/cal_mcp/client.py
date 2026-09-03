import httpx
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cal_mcp.log")),
    ],
)
logger = logging.getLogger(__name__)

CAL_BASE_URL = os.getenv("CAL_BASE_URL", "https://api.cal.com/v2")
CAL_TIMEZONE = os.getenv("CAL_TIMEZONE", "Asia/Karachi")


def get_headers(api_version: str = "2024-08-13"):
    return {
        "Authorization": f"Bearer {os.getenv('CAL_API_KEY')}",
        "Content-Type": "application/json",
        "cal-api-version": api_version
    }


# ── Error handling helpers ────────────────────────────────────────────────────

def _handle_http_error(e: httpx.HTTPStatusError, operation: str) -> dict:
    try:
        detail = e.response.json()
    except Exception:
        detail = e.response.text
    logger.error(f"[{operation}] HTTP {e.response.status_code} — {detail}")
    return {
        "error": True,
        "operation": operation,
        "status_code": e.response.status_code,
        "detail": detail,
    }


def _handle_unexpected_error(e: Exception, operation: str) -> dict:
    logger.exception(f"[{operation}] Unexpected error: {e}")
    return {
        "error": True,
        "operation": operation,
        "detail": str(e),
    }


# ── API functions ─────────────────────────────────────────────────────────────

async def get_event_types() -> dict:
    logger.info("[get_event_types] Fetching event types")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CAL_BASE_URL}/event-types",
                headers=get_headers("2024-06-14")
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"[get_event_types] Success — {len(data.get('data', []))} event types returned")
            return data
    except httpx.HTTPStatusError as e:
        return _handle_http_error(e, "get_event_types")
    except Exception as e:
        return _handle_unexpected_error(e, "get_event_types")


async def get_availability(username: str, event_type_slug: str, start: str, end: str,
                            timezone: str = None) -> dict:
    """
    FIX: Added timezone param so Cal.com returns slots in local time, not UTC.
    Without this, slots were shown in UTC which made them appear shifted by 5 hours
    for Asia/Karachi users.
    """
    tz = timezone or CAL_TIMEZONE
    logger.info(f"[get_availability] user={username} slug={event_type_slug} {start}→{end} tz={tz}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CAL_BASE_URL}/slots",
                headers=get_headers("2024-09-04"),
                params={
                    "username": username,
                    "eventTypeSlug": event_type_slug,
                    "start": start,
                    "end": end,
                    "timeZone": tz,       # ← THE FIX: tells Cal.com which timezone to use
                }
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"[get_availability] Success — slots for {list(data.get('data', {}).keys())}")
            return data
    except httpx.HTTPStatusError as e:
        return _handle_http_error(e, "get_availability")
    except Exception as e:
        return _handle_unexpected_error(e, "get_availability")


async def get_bookings(date_from: str = None, date_to: str = None,
                        status: str = "upcoming") -> dict:
    """
    NEW: Fetch all bookings, optionally filtered by date range and status.
    This is what enables 'cancel all meetings for tomorrow' — the LLM first
    calls this to get UIDs, then calls cancel_booking for each one.

    status options: upcoming, recurring, past, cancelled, unconfirmed
    date_from / date_to: ISO date strings e.g. 2026-04-01
    """
    logger.info(f"[get_bookings] status={status} from={date_from} to={date_to}")
    try:
        params = {"status": status}
        if date_from:
            params["afterStart"] = date_from
        if date_to:
            params["beforeEnd"] = date_to

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CAL_BASE_URL}/bookings",
                headers=get_headers("2024-08-13"),
                params=params
            )
            response.raise_for_status()
            data = response.json()
            bookings = data.get("data", {}).get("bookings", [])
            logger.info(f"[get_bookings] Success — {len(bookings)} bookings returned")
            return data
    except httpx.HTTPStatusError as e:
        return _handle_http_error(e, "get_bookings")
    except Exception as e:
        return _handle_unexpected_error(e, "get_bookings")


async def create_booking(data: dict) -> dict:
    logger.info(f"[create_booking] eventTypeId={data.get('eventTypeId')} start={data.get('start')} attendee={data.get('attendee', {}).get('email')}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CAL_BASE_URL}/bookings",
                headers=get_headers("2024-08-13"),
                json=data
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"[create_booking] Success — uid={result.get('data', {}).get('uid')}")
            return result
    except httpx.HTTPStatusError as e:
        return _handle_http_error(e, "create_booking")
    except Exception as e:
        return _handle_unexpected_error(e, "create_booking")


async def cancel_booking(booking_uid: str, reason: str = "Cancelled by user") -> dict:
    logger.info(f"[cancel_booking] uid={booking_uid} reason='{reason}'")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CAL_BASE_URL}/bookings/{booking_uid}/cancel",
                headers=get_headers("2024-08-13"),
                json={"cancellationReason": reason}
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"[cancel_booking] Success — uid={booking_uid}")
            return result
    except httpx.HTTPStatusError as e:
        return _handle_http_error(e, "cancel_booking")
    except Exception as e:
        return _handle_unexpected_error(e, "cancel_booking")


async def reschedule_booking(booking_uid: str, new_start: str, reason: str = "") -> dict:
    logger.info(f"[reschedule_booking] uid={booking_uid} new_start={new_start}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CAL_BASE_URL}/bookings/{booking_uid}/reschedule",
                headers=get_headers("2024-08-13"),
                json={
                    "start": new_start,
                    "reschedulingReason": reason
                }
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"[reschedule_booking] Success — new uid={result.get('data', {}).get('uid')}")
            return result
    except httpx.HTTPStatusError as e:
        return _handle_http_error(e, "reschedule_booking")
    except Exception as e:
        return _handle_unexpected_error(e, "reschedule_booking")