"""Tests for the new ICS sync implementation."""

import tempfile
from datetime import datetime
from pathlib import Path

from icalendar import Event

from src.ics_sync import (
    OrgEvent,
    merge_events,
    parse_ics_event,
    parse_org_file,
    write_org_file,
)


def create_test_ics_event(
    uid: str = "test123",
    summary: str = "Test Event",
    start: datetime | None = None,
    end: datetime | None = None,
    location: str = "Room A",
    description: str = "Test description",
) -> Event:
    """Helper to create test ICS events."""
    event = Event()
    event.add("UID", uid)
    event.add("SUMMARY", summary)
    event.add("DTSTART", start or datetime(2025, 1, 15, 14, 0))
    if end:
        event.add("DTEND", end)
    if location:
        event.add("LOCATION", location)
    if description:
        event.add("DESCRIPTION", description)
    event.add("STATUS", "CONFIRMED")
    return event


def test_parse_ics_event() -> None:
    """Test parsing a single ICS event."""
    ics_event = create_test_ics_event()
    org_event = parse_ics_event(ics_event)

    assert org_event is not None
    assert org_event.uid == "test123"
    assert org_event.summary == "Test Event"
    assert org_event.location == "Room A"
    assert org_event.description == "Test description"
    assert org_event.status == "CONFIRMED"


def test_org_event_to_org() -> None:
    """Test converting OrgEvent to org format."""
    event = OrgEvent(
        uid="test123",
        summary="Team Meeting",
        start=datetime(2025, 1, 15, 14, 0),
        end=datetime(2025, 1, 15, 15, 0),
        location="Conference Room",
        description="Discuss project status",
        status="CONFIRMED",
        categories="Work",
        user_notes="Remember to bring laptop\nAsk about deadline",
    )

    org_text = event.to_org()

    assert "* Team Meeting" in org_text
    assert ":UID:           test123" in org_text
    assert ":LOCATION:      Conference Room" in org_text
    assert ":DESCRIPTION:   Discuss project status" in org_text
    assert "<2025-01-15 Wed 14:00-15:00>" in org_text
    assert "Remember to bring laptop" in org_text
    assert "Ask about deadline" in org_text


def test_org_event_all_day() -> None:
    """Test all-day event formatting."""
    event = OrgEvent(
        uid="allday123",
        summary="Conference",
        start=datetime(2025, 1, 15, 0, 0),
        end=None,  # All-day event
        location="NYC",
        description="Annual conference",
        status="CONFIRMED",
        categories=None,
    )

    org_text = event.to_org()
    assert "<2025-01-15 Wed>" in org_text  # No time for all-day


def test_merge_events_new_event() -> None:
    """Test adding a new event."""
    existing: dict[str, OrgEvent] = {}
    new: dict[str, OrgEvent] = {
        "new123": OrgEvent(
            uid="new123",
            summary="New Meeting",
            start=datetime(2025, 1, 20, 10, 0),
            end=datetime(2025, 1, 20, 11, 0),
            location="Room B",
            description="New meeting description",
            status="CONFIRMED",
            categories=None,
        )
    }

    merged = merge_events(existing, new)

    assert len(merged) == 1
    assert "new123" in merged
    assert merged["new123"].summary == "New Meeting"


def test_merge_events_update_existing() -> None:
    """Test updating an existing event while preserving notes."""
    existing: dict[str, OrgEvent] = {
        "meet123": OrgEvent(
            uid="meet123",
            summary="Old Title",
            start=datetime(2025, 1, 15, 9, 0),
            end=datetime(2025, 1, 15, 10, 0),
            location="Old Room",
            description="Old description",
            status="CONFIRMED",
            categories=None,
            user_notes="My important notes\nDon't forget this!",
        )
    }

    new: dict[str, OrgEvent] = {
        "meet123": OrgEvent(
            uid="meet123",
            summary="New Title",
            start=datetime(2025, 1, 15, 10, 0),  # Time changed
            end=datetime(2025, 1, 15, 11, 0),
            location="New Room",  # Location changed
            description="New description",
            status="CONFIRMED",
            categories=None,
        )
    }

    merged = merge_events(existing, new)

    assert len(merged) == 1
    assert merged["meet123"].summary == "New Title"
    assert merged["meet123"].location == "New Room"
    assert merged["meet123"].start.hour == 10
    assert merged["meet123"].user_notes == "My important notes\nDon't forget this!"


def test_merge_events_mark_cancelled() -> None:
    """Test marking removed events as cancelled."""
    existing: dict[str, OrgEvent] = {
        "cancel123": OrgEvent(
            uid="cancel123",
            summary="To Be Cancelled",
            start=datetime(2025, 1, 15, 14, 0),
            end=datetime(2025, 1, 15, 15, 0),
            location="Room C",
            description="Will be cancelled",
            status="CONFIRMED",
            categories=None,
            user_notes="Some notes",
        )
    }

    new: dict[str, OrgEvent] = {}  # Event not in new calendar

    merged = merge_events(existing, new)

    assert len(merged) == 1
    assert merged["cancel123"].status == "CANCELLED"
    assert merged["cancel123"].user_notes == "Some notes"  # Notes preserved

    # Check org output includes CANCELLED prefix
    org_text = merged["cancel123"].to_org()
    assert "* CANCELLED: To Be Cancelled" in org_text


def test_parse_org_file() -> None:
    """Test parsing an org file."""
    org_content = """* Team Standup
:PROPERTIES:
:UID:           standup123
:LOCATION:      Zoom
:DESCRIPTION:   Daily standup meeting
:STATUS:        CONFIRMED
:CATEGORIES:    Work
:END:
<2025-01-15 Wed 09:00-09:30>

These are my notes
- Discuss blockers
- Update on tasks

* CANCELLED: Old Meeting
:PROPERTIES:
:UID:           old123
:LOCATION:      Room X
:STATUS:        CANCELLED
:END:
<2025-01-10 Fri 14:00-15:00>

This was cancelled last minute
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        f.write(org_content)
        temp_path = f.name

    try:
        events = parse_org_file(temp_path)

        assert len(events) == 2

        # Check first event
        assert "standup123" in events
        standup = events["standup123"]
        assert standup.summary == "Team Standup"
        assert standup.location == "Zoom"
        assert standup.description == "Daily standup meeting"
        assert "Discuss blockers" in standup.user_notes
        assert "Update on tasks" in standup.user_notes

        # Check cancelled event
        assert "old123" in events
        old = events["old123"]
        assert old.summary == "Old Meeting"  # CANCELLED prefix removed in parsing
        assert old.status == "CANCELLED"
        assert "cancelled last minute" in old.user_notes
    finally:
        Path(temp_path).unlink()


def test_write_org_file() -> None:
    """Test writing events to org file."""
    events: dict[str, OrgEvent] = {
        "meet1": OrgEvent(
            uid="meet1",
            summary="Morning Meeting",
            start=datetime(2025, 1, 15, 9, 0),
            end=datetime(2025, 1, 15, 10, 0),
            location="Room A",
            description="Team sync",
            status="CONFIRMED",
            categories="Work",
            user_notes="Bring coffee",
        ),
        "meet2": OrgEvent(
            uid="meet2",
            summary="Afternoon Review",
            start=datetime(2025, 1, 15, 14, 0),
            end=datetime(2025, 1, 15, 15, 0),
            location="Room B",
            description="Code review",
            status="CONFIRMED",
            categories="Dev",
            user_notes="Review PR #123",
        ),
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        temp_path = f.name

    try:
        write_org_file(events, temp_path)

        with open(temp_path) as f:
            content = f.read()

        # Check both events are present
        assert "* Morning Meeting" in content
        assert "* Afternoon Review" in content

        # Check they're sorted by time
        morning_pos = content.index("Morning Meeting")
        afternoon_pos = content.index("Afternoon Review")
        assert morning_pos < afternoon_pos

        # Check date header
        assert "# Wednesday, January 15, 2025" in content

        # Check user notes are included
        assert "Bring coffee" in content
        assert "Review PR #123" in content
    finally:
        Path(temp_path).unlink()


def test_end_to_end_sync() -> None:
    """Test the complete sync process."""
    # Create initial org file with existing event and notes
    initial_org = """* Project Planning
:PROPERTIES:
:UID:           project123
:LOCATION:      Conference Room
:DESCRIPTION:   Q1 planning session
:STATUS:        CONFIRMED
:END:
<2025-01-20 Mon 10:00-12:00>

My notes from last time:
- Budget needs review
- Timeline is tight
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        f.write(initial_org)
        org_path = f.name

    try:
        # Parse existing
        existing = parse_org_file(org_path)

        # Simulate new events from ICS (with updated info)
        new: dict[str, OrgEvent] = {
            "project123": OrgEvent(
                uid="project123",
                summary="Project Planning (Updated)",  # Title changed
                start=datetime(2025, 1, 20, 14, 0),  # Time changed
                end=datetime(2025, 1, 20, 16, 0),
                location="Zoom",  # Location changed
                description="Q1 planning - now remote",  # Description changed
                status="CONFIRMED",
                categories=None,
            ),
            "standup456": OrgEvent(
                uid="standup456",
                summary="Daily Standup",  # New event
                start=datetime(2025, 1, 21, 9, 0),
                end=datetime(2025, 1, 21, 9, 30),
                location="Slack",
                description="Quick sync",
                status="CONFIRMED",
                categories=None,
            ),
        }

        # Merge
        merged = merge_events(existing, new)

        # Write back
        write_org_file(merged, org_path)

        # Read and verify
        with open(org_path) as f:
            final_content = f.read()

        # Check updates applied
        assert "Project Planning (Updated)" in final_content
        assert "Zoom" in final_content
        assert "Q1 planning - now remote" in final_content

        # Check notes preserved
        assert "Budget needs review" in final_content
        assert "Timeline is tight" in final_content

        # Check new event added
        assert "Daily Standup" in final_content
        assert "Slack" in final_content

    finally:
        Path(org_path).unlink()
