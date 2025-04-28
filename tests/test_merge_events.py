from datetime import datetime, timedelta
from sync_calendar import merge_events


def test_merge_new_event():
    """Test merging a new event that doesn't exist in existing events"""
    existing_events = {}

    from src.sync_calendar import OrgEvent

    new_events = {
        "event1": OrgEvent(
            id="event1",
            title="New Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED"},
            scheduling="<2025-05-01 Thu 09:00-10:00>",
            content="New event content",
        )
    }

    merged = merge_events(existing_events, new_events)

    assert len(merged) == 1
    assert "event1" in merged
    assert merged["event1"].title == "New Event"
    assert "#+begin_agenda" in merged["event1"].content
    assert "New event content" in merged["event1"].content


def test_merge_updated_event():
    """Test merging an event that exists in both with updates"""
    from src.sync_calendar import OrgEvent

    existing_events = {
        "event1": OrgEvent(
            id="event1",
            title="Existing Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED", "LOCATION": "Room A"},
            scheduling="<2025-05-01 Thu 09:00-10:00>",
            content="#+begin_agenda\nOld content\n#+end_agenda\n\nUser notes",
        )
    }

    new_events = {
        "event1": OrgEvent(
            id="event1",
            title="Updated Event",  # Title changed
            properties={
                "ID": "event1",
                "STATUS": "CONFIRMED",
                "LOCATION": "Room B",
            },  # Location changed
            scheduling="<2025-05-01 Thu 10:00-11:00>",  # Time changed
            content="Updated content",
        )
    }

    merged = merge_events(existing_events, new_events)

    assert len(merged) == 1
    assert merged["event1"].title == "Updated Event"  # Should use new title
    assert merged["event1"].properties.get("LOCATION") == "Room B"  # Should use new properties
    assert (
        merged["event1"].scheduling == "<2025-05-01 Thu 10:00-11:00>"
    )  # Should use new scheduling
    assert "Updated content" in merged["event1"].content  # Should update agenda
    assert "User notes" in merged["event1"].content  # Should preserve user notes


def test_mark_canceled_events():
    """Test that events no longer in calendar are marked as canceled"""
    from src.sync_calendar import OrgEvent

    existing_events = {
        "event1": OrgEvent(
            id="event1",
            title="Existing Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED"},
            scheduling="<2025-05-01 Thu 09:00-10:00>",
            content="Event content",
        )
    }

    new_events = {}  # Event no longer in calendar

    merged = merge_events(existing_events, new_events)

    assert len(merged) == 1
    assert merged["event1"].title == "CANCELLED: Existing Event"
    assert merged["event1"].properties.get("STATUS") == "CANCELLED"


def test_preserve_past_events():
    """Test that past events are preserved as-is"""
    # Create a past event
    from src.sync_calendar import OrgEvent

    past_event = {
        "event1": OrgEvent(
            id="event1",
            title="Past Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED"},
            scheduling="<2023-01-01 Sun 09:00-10:00>",  # Past date
            content="Past event content",
        )
    }

    # New version of the event with changes
    new_events = {
        "event1": OrgEvent(
            id="event1",
            title="Updated Past Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED", "LOCATION": "New Room"},
            scheduling="<2023-01-01 Sun 10:00-11:00>",
            content="Updated content",
        )
    }

    # With default days_backward=0, past event should be preserved as-is
    merged = merge_events(past_event, new_events)

    assert len(merged) == 1
    # Past event should be preserved as-is
    assert merged["event1"].title == "Past Event"
    assert merged["event1"].properties.get("LOCATION") is None
    assert merged["event1"].scheduling == "<2023-01-01 Sun 09:00-10:00>"
    assert merged["event1"].content == "Past event content"


def test_past_events_with_days_backward():
    """Test that days_backward parameter affects how past events are handled"""
    from src.sync_calendar import OrgEvent

    # Create a more recent past event (that could be within days_backward)
    # Use a date that's 5 days in the past
    past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    past_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
        (datetime.now() - timedelta(days=5)).weekday()
    ]

    recent_past_event = {
        "event1": OrgEvent(
            id="event1",
            title="Recent Past Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED"},
            scheduling=f"<{past_date} {past_day} 09:00-10:00>",  # 5 days ago
            content="Original content",
        )
    }

    # New version of the event with changes
    new_events = {
        "event1": OrgEvent(
            id="event1",
            title="Updated Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED", "LOCATION": "New Room"},
            scheduling=f"<{past_date} {past_day} 10:00-11:00>",  # Same date, different time
            content="Updated content",
        )
    }

    # With days_backward=0, even recent past event should be preserved
    merged_without_backward = merge_events(recent_past_event, new_events, days_backward=0)
    assert (
        merged_without_backward["event1"].title == "Recent Past Event"
    )  # Original title preserved

    # With days_backward=7, the 5-day old event should be updated
    merged_with_backward = merge_events(recent_past_event, new_events, days_backward=7)
    assert merged_with_backward["event1"].title == "Updated Event"  # Updated with new title
    assert (
        merged_with_backward["event1"].properties.get("LOCATION") == "New Room"
    )  # Updated properties


def test_agenda_block_creation():
    """Test that agenda blocks are properly created for new events"""
    from src.sync_calendar import OrgEvent

    new_events = {
        "event1": OrgEvent(
            id="event1",
            title="New Event",
            properties={"ID": "event1", "STATUS": "CONFIRMED"},
            scheduling="<2025-05-01 Thu 09:00-10:00>",
            content="Description text",
        )
    }

    merged = merge_events({}, new_events)

    assert "#+begin_agenda\nDescription text\n#+end_agenda" in merged["event1"].content
