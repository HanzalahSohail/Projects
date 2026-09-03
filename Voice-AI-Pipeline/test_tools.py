"""
Test script — verify tools work without the voice pipeline.

Run: python test_tools.py
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from tools import registry
from tools.messaging import register_messaging_tools
from tools.crm import register_crm_tools
from tools.scheduling import register_scheduling_tools


async def main():
    print("=" * 60)
    print("  Tool Calling Test Suite")
    print("=" * 60)

    # Step 1: Register tools
    register_messaging_tools()
    register_crm_tools()
    register_scheduling_tools()

    print(f"\n✓ {len(registry.list_tools())} tools registered:")
    for name in registry.list_tools():
        print(f"  - {name}")

    # Step 2: Verify OpenAI schemas
    schemas = registry.get_openai_tools()
    print(f"\n✓ OpenAI tool schemas generated ({len(schemas)} tools)")
    for s in schemas:
        fn = s["function"]
        print(f"  - {fn['name']}: {len(fn['parameters'].get('properties', {}))} params")

    # Step 3: Test create_lead (local, always works)
    print("\n─── Testing create_lead ───")
    result = await registry.execute("create_lead", {
        "name": "Test User",
        "phone": "+1234567890",
        "email": "test@example.com",
        "company": "Test Corp",
        "notes": "Created by test script"
    })
    print(f"  Success: {result.success}")
    print(f"  Result: {result.result}")
    print(f"  Time: {result.execution_time_ms}ms")

    # Step 4: Test log_call_summary (local, always works)
    print("\n─── Testing log_call_summary ───")
    result = await registry.execute("log_call_summary", {
        "caller_name": "Test User",
        "summary": "Test call about product demo",
        "duration_seconds": 120,
        "outcome": "completed",
        "follow_up": "Send pricing doc"
    })
    print(f"  Success: {result.success}")
    print(f"  Result: {result.result}")

    # Step 5: Test get_availability (returns mock if no Cal.com key)
    print("\n─── Testing get_availability ───")
    result = await registry.execute("get_availability", {
        "date": "2025-06-15",
        "timezone": "America/New_York"
    })
    print(f"  Success: {result.success}")
    print(f"  Slots: {json.dumps(result.result, indent=2)[:200]}...")

    # Step 6: Test book_meeting (returns mock)
    print("\n─── Testing book_meeting ───")
    result = await registry.execute("book_meeting", {
        "name": "Test User",
        "email": "test@example.com",
        "start_time": "2025-06-15T10:00:00"
    })
    print(f"  Success: {result.success}")
    print(f"  Result: {result.result}")

    # Step 7: Test cancel_meeting (returns mock)
    print("\n─── Testing cancel_meeting ───")
    result = await registry.execute("cancel_meeting", {
        "booking_id": "mock-12345",
        "reason": "Rescheduling"
    })
    print(f"  Success: {result.success}")
    print(f"  Result: {result.result}")

    # Step 8: Test send_sms (will fail without Twilio creds, that's OK)
    print("\n─── Testing send_sms (expects Twilio config) ───")
    result = await registry.execute("send_sms", {
        "to": "923107014959",
        "message": "Test message"
    })
    print(f"  Success: {result.success}")
    if not result.success:
        print(f"  Expected: {result.error or result.result}")

    # Step 9: Test send_email (will fail without SMTP creds, that's OK)
    print("\n─── Testing send_email (expects SMTP config) ───")
    result = await registry.execute("send_email", {
        "to": "test@example.com",
        "subject": "Test",
        "body": "Test email body"
    })
    print(f"  Success: {result.success}")
    if not result.success:
        print(f"  Expected: {result.error or result.result}")

    # Step 10: Test unknown tool
    print("\n─── Testing unknown tool ───")
    result = await registry.execute("nonexistent_tool", {})
    print(f"  Success: {result.success} (expected False)")
    print(f"  Error: {result.error}")

    print("\n" + "=" * 60)
    print("  All tests complete!")
    print("=" * 60)

    # Verify data files
    from pathlib import Path
    data_dir = Path(__file__).parent / "data"
    leads_file = data_dir / "leads.json"
    logs_file = data_dir / "call_logs.json"
    print(f"\n  Leads file: {leads_file} ({'exists' if leads_file.exists() else 'missing'})")
    print(f"  Logs file:  {logs_file} ({'exists' if logs_file.exists() else 'missing'})")


if __name__ == "__main__":
    asyncio.run(main())