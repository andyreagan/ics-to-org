"""Integration tests with real ICS files and org files."""

import tempfile
from pathlib import Path

from icalendar import Calendar

from src.ics_sync import (
    merge_events,
    parse_ics_calendar,
    parse_org_file,
    write_org_file,
)


def test_complete_sync_workflow() -> None:
    """Test the complete sync workflow with realistic data."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    # Step 1: Parse initial ICS file
    with open(fixtures_dir / "sample_calendar.ics", "rb") as f:
        initial_cal = Calendar.from_ical(f.read())

    initial_events = parse_ics_calendar(initial_cal, days_forward=365, days_backward=365)

    # Verify we got the expected events
    assert len(initial_events) == 4
    assert "standup-123@company.com" in initial_events
    assert "project-meeting-456@company.com" in initial_events
    assert "allday-event-789@company.com" in initial_events
    assert "recurring-lunch-999@company.com" in initial_events

    # Step 2: Create initial org file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        org_path = f.name

    try:
        write_org_file(initial_events, org_path)

        # Verify initial org file was created correctly
        with open(org_path) as f:
            initial_content = f.read()

        assert "* Daily Standup" in initial_content
        assert "* Project Planning Session" in initial_content
        assert "* Company Retreat" in initial_content
        assert "* Team Lunch" in initial_content
        assert ":UID:           standup-123@company.com" in initial_content

        # Step 3: Simulate user adding notes
        # Copy our prepared org file with user notes
        with open(fixtures_dir / "existing_calendar.org") as f:
            user_content = f.read()

        with open(org_path, "w") as f:
            f.write(user_content)

        # Step 4: Parse existing org file with user notes
        existing_events = parse_org_file(org_path)

        # Verify user notes were preserved
        standup = existing_events["standup-123@company.com"]
        assert "Need to finish the authentication module" in standup.user_notes
        assert "Blocked on database migration" in standup.user_notes

        project_meeting = existing_events["project-meeting-456@company.com"]
        assert "Marketing wants earlier launch date" in project_meeting.user_notes
        assert "Get cost estimates from vendors" in project_meeting.user_notes

        # Step 5: Parse updated ICS file (with changes)
        with open(fixtures_dir / "updated_calendar.ics", "rb") as f:
            updated_cal = Calendar.from_ical(f.read())

        new_events = parse_ics_calendar(updated_cal, days_forward=365, days_backward=365)

        # Verify changes in new calendar
        assert len(new_events) == 4  # One removed, one added
        assert "recurring-lunch-999@company.com" not in new_events  # Removed
        assert "new-event-111@company.com" in new_events  # Added

        # Check updated standup time
        updated_standup = new_events["standup-123@company.com"]
        assert updated_standup.summary == "Daily Standup (Moved)"
        assert updated_standup.start.hour == 15  # Moved from 14 to 15
        assert updated_standup.location == "Zoom Room B"  # Changed room

        # Step 6: Merge events
        merged_events = merge_events(existing_events, new_events)

        # Step 7: Write merged result
        write_org_file(merged_events, org_path)

        # Step 8: Verify final result
        with open(org_path) as f:
            final_content = f.read()

        # Verify updates were applied
        assert "* Daily Standup (Moved)" in final_content
        assert "Zoom Room B" in final_content
        assert "15:00-15:30" in final_content

        # Verify user notes were preserved
        assert "Need to finish the authentication module" in final_content
        assert "Marketing wants earlier launch date" in final_content

        # Verify cancelled events
        assert "* CANCELLED: Team Lunch" in final_content
        assert "CANCELLED: Company Retreat" in final_content

        # Verify new event added
        assert "* Client Demo" in final_content
        assert "Client Office" in final_content

        print("✅ Complete sync workflow test passed!")

    finally:
        Path(org_path).unlink()


def test_specific_merge_scenarios() -> None:
    """Test specific merge scenarios with realistic data."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    # Parse the existing org file with user notes
    existing_events = parse_org_file(str(fixtures_dir / "existing_calendar.org"))

    # Parse updated ICS
    with open(fixtures_dir / "updated_calendar.ics", "rb") as f:
        cal = Calendar.from_ical(f.read())
    new_events = parse_ics_calendar(cal, days_forward=365, days_backward=365)

    # Merge
    merged = merge_events(existing_events, new_events)

    # Test 1: Updated event preserves notes
    standup = merged["standup-123@company.com"]
    assert standup.summary == "Daily Standup (Moved)"  # Updated from ICS
    assert standup.location == "Zoom Room B"  # Updated from ICS
    assert "Need to finish the authentication module" in standup.user_notes  # Preserved

    # Test 2: Extended meeting preserves action items
    project = merged["project-meeting-456@company.com"]
    assert project.summary == "Extended Project Planning Session"  # Updated
    assert project.end is not None and project.end.hour == 18  # Extended to 2 hours
    assert "[ ] Get cost estimates from vendors" in project.user_notes  # Preserved

    # Test 3: Cancelled event marked correctly
    lunch = merged["recurring-lunch-999@company.com"]
    assert lunch.status == "CANCELLED"  # Marked as cancelled
    assert "Try their new seafood special" in lunch.user_notes  # Notes preserved

    # Test 4: ICS-cancelled event stays cancelled but preserves notes
    retreat = merged["allday-event-789@company.com"]
    assert retreat.status == "CANCELLED"  # From ICS
    assert "Hiking boots" in retreat.user_notes  # Notes preserved

    # Test 5: New event has no user notes initially
    demo = merged["new-event-111@company.com"]
    assert demo.summary == "Client Demo"
    assert demo.user_notes == ""  # No notes yet


def test_edge_cases() -> None:
    """Test edge cases and error conditions."""
    # Test 1: Empty ICS file
    empty_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR"""

    cal = Calendar.from_ical(empty_ics.encode())
    events = parse_ics_calendar(cal)
    assert len(events) == 0

    # Test 2: ICS with invalid events (no UID)
    invalid_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
DTSTART:20250115T140000Z
DTEND:20250115T143000Z
SUMMARY:No UID Event
END:VEVENT
END:VCALENDAR"""

    cal = Calendar.from_ical(invalid_ics.encode())
    events = parse_ics_calendar(cal)
    assert len(events) == 0  # Should skip events without UID

    # Test 3: Org file with malformed events
    malformed_org = """* Good Event
:PROPERTIES:
:UID:           good-123
:END:
<2025-01-15 Wed 14:00>

* Bad Event Without UID
:PROPERTIES:
:STATUS:        CONFIRMED
:END:
<2025-01-16 Thu 15:00>

* Another Good Event
:PROPERTIES:
:UID:           good-456
:END:
<2025-01-17 Fri 16:00>
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        f.write(malformed_org)
        temp_path = f.name

    try:
        events = parse_org_file(temp_path)
        # Should only parse events with UID
        assert len(events) == 2
        assert "good-123" in events
        assert "good-456" in events
    finally:
        Path(temp_path).unlink()


def test_date_formatting() -> None:
    """Test that dates are formatted correctly in different scenarios."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    with open(fixtures_dir / "sample_calendar.ics", "rb") as f:
        cal = Calendar.from_ical(f.read())

    events = parse_ics_calendar(cal, days_forward=365, days_backward=365)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        org_path = f.name

    try:
        write_org_file(events, org_path)

        with open(org_path) as f:
            content = f.read()

        # Test timed events
        assert "<2025-01-15 Wed 14:00-14:30>" in content  # Standup
        assert "<2025-01-16 Thu 16:00-17:00>" in content  # Project meeting

        # Test all-day events
        assert "<2025-01-20 Mon>" in content  # Company retreat (no time)

        # Test date headers
        assert "# Wednesday, January 15, 2025" in content
        assert "# Thursday, January 16, 2025" in content
        assert "# Monday, January 20, 2025" in content

    finally:
        Path(org_path).unlink()


def test_user_notes_preservation() -> None:
    """Test various formats of user notes are preserved correctly."""
    org_with_various_notes = """* Meeting with Complex Notes
:PROPERTIES:
:UID:           complex-123
:END:
<2025-01-15 Wed 14:00>

Regular paragraph notes here.

## Markdown-style heading
- Bullet point
- Another bullet point
  - Nested bullet

1. Numbered list
2. Second item

| Table | Data |
|-------|------|
| A     | B    |

```
Code block
with multiple lines
```

#+BEGIN_SRC python
print("org-mode code block")
#+END_SRC

> Quoted text
> Multiple lines

Final paragraph with **bold** and *italic* text.
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".org", delete=False) as f:
        f.write(org_with_various_notes)
        temp_path = f.name

    try:
        # Parse org file
        events = parse_org_file(temp_path)
        event = events["complex-123"]

        # Verify all different note formats are preserved
        assert "Regular paragraph notes here." in event.user_notes
        assert "## Markdown-style heading" in event.user_notes
        assert "- Bullet point" in event.user_notes
        assert "  - Nested bullet" in event.user_notes
        assert "1. Numbered list" in event.user_notes
        assert "| Table | Data |" in event.user_notes
        assert "```" in event.user_notes
        assert "Code block" in event.user_notes
        assert "#+BEGIN_SRC python" in event.user_notes
        assert "> Quoted text" in event.user_notes
        assert "**bold** and *italic*" in event.user_notes

        # Create a dummy new event (no changes)
        new_events = {"complex-123": event}
        merged = merge_events(events, new_events)

        # Write back and verify notes are still there
        write_org_file(merged, temp_path)

        with open(temp_path) as f:
            final_content = f.read()

        # All formatting should be preserved
        assert "Regular paragraph notes here." in final_content
        assert "## Markdown-style heading" in final_content
        assert "- Bullet point" in final_content
        assert "#+BEGIN_SRC python" in final_content

    finally:
        Path(temp_path).unlink()


if __name__ == "__main__":
    # Run the main integration test
    test_complete_sync_workflow()
    test_specific_merge_scenarios()
    test_edge_cases()
    test_date_formatting()
    test_user_notes_preservation()
    print("🎉 All integration tests passed!")
