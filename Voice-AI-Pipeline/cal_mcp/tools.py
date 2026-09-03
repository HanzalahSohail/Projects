import json
import re
import logging
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from cal_mcp.client import (
    get_event_types,
    get_availability,
    create_booking,
    cancel_booking,
    reschedule_booking,
)

logger = logging.getLogger(__name__)

# ── Validation helpers ────────────────────────────────────────────────────────

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_iso_date(value: str, field: str) -> str | None:
    if not ISO_DATE_RE.match(value):
        return f"'{field}' must be in YYYY-MM-DD format (got: '{value}')"
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return f"'{field}' is not a valid calendar date (got: '{value}')"
    return None


def _validate_iso_datetime(value: str, field: str) -> str | None:
    if not ISO_DATETIME_RE.match(value):
        return f"'{field}' must be ISO 8601 UTC format e.g. 2026-03-18T10:00:00Z (got: '{value}')"
    return None


def _validate_email(value: str, field: str) -> str | None:
    if not EMAIL_RE.match(value):
        return f"'{field}' must be a valid email address (got: '{value}')"
    return None


def _validate_non_empty(value: str, field: str) -> str | None:
    if not value or not value.strip():
        return f"'{field}' must not be empty"
    return None


def _error_response(errors: list[str]) -> str:
    logger.warning(f"[validation] Errors: {errors}")
    return json.dumps({"error": True, "validation_errors": errors}, indent=2)


# ── Tool registration ─────────────────────────────────────────────────────────

def register_tools(mcp: FastMCP):

    @mcp.tool()
    async def list_event_types() -> str:
        """List all event types available on your Cal.com account."""
        result = await get_event_types()
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def get_availability_slots(
        username: str,
        event_type_slug: str,
        start: str,
        end: str,
    ) -> str:
        """
        Get available time slots for a given event type and date range.

        Args:
            username: Cal.com username e.g. hanzalah-rc
            event_type_slug: Event type slug e.g. 15min or 30min
            start: Start date in ISO format e.g. 2026-03-18
            end: End date in ISO format e.g. 2026-03-20
        """
        errors = []
        for field, value in [("username", username), ("event_type_slug", event_type_slug)]:
            if err := _validate_non_empty(value, field):
                errors.append(err)
        if err := _validate_iso_date(start, "start"):
            errors.append(err)
        if err := _validate_iso_date(end, "end"):
            errors.append(err)
        if not errors:
            if datetime.strptime(start, "%Y-%m-%d") >= datetime.strptime(end, "%Y-%m-%d"):
                errors.append(f"'start' ({start}) must be before 'end' ({end})")
        if errors:
            return _error_response(errors)

        result = await get_availability(username, event_type_slug, start, end)
        return json.dumps(result, indent=2) #converting to string for AI to use

    @mcp.tool()
    async def create_new_booking(
        event_type_id: int,
        start: str,
        attendee_name: str,
        attendee_email: str,
        timezone: str,
    ) -> str:
        """
        Create a new booking on Cal.com.

        Args:
            event_type_id: The ID of the event type to book
            start: Start time in ISO 8601 format e.g. 2026-03-18T10:00:00Z
            attendee_name: Full name of the attendee
            attendee_email: Email of the attendee
            timezone: Timezone of the attendee e.g. Asia/Karachi
        """
        errors = []
        if event_type_id <= 0:
            errors.append(f"'event_type_id' must be a positive integer (got: {event_type_id})")
        if err := _validate_iso_datetime(start, "start"):
            errors.append(err)
        for field, value in [("attendee_name", attendee_name), ("timezone", timezone)]:
            if err := _validate_non_empty(value, field):
                errors.append(err)
        if err := _validate_email(attendee_email, "attendee_email"):
            errors.append(err)
        if errors:
            return _error_response(errors)

        data = {
            "eventTypeId": event_type_id,
            "start": start,
            "attendee": {
                "name": attendee_name,
                "email": attendee_email,
                "timeZone": timezone,
            },
        }
        result = await create_booking(data)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def cancel_existing_booking(
        booking_uid: str,
        reason: str = "Cancelled by user",
    ) -> str:
        """
        Cancel an existing booking using its UID.

        Args:
            booking_uid: The unique ID of the booking to cancel
            reason: Reason for cancellation
        """
        errors = []
        if err := _validate_non_empty(booking_uid, "booking_uid"):
            errors.append(err)
        if errors:
            return _error_response(errors)

        result = await cancel_booking(booking_uid, reason)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def reschedule_existing_booking(
        booking_uid: str,
        new_start: str,
        reason: str = "",
    ) -> str:
        """
        Reschedule an existing booking to a new time.

        Args:
            booking_uid: The unique ID of the booking to reschedule
            new_start: New start time in ISO 8601 format e.g. 2026-03-19T14:00:00Z
            reason: Reason for rescheduling
        """
        errors = []
        if err := _validate_non_empty(booking_uid, "booking_uid"):
            errors.append(err)
        if err := _validate_iso_datetime(new_start, "new_start"):
            errors.append(err)
        if errors:
            return _error_response(errors)

        result = await reschedule_booking(booking_uid, new_start, reason)
        return json.dumps(result, indent=2)
    