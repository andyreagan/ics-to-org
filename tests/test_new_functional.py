import sys
import os
import logging

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.sync_calendar import parse_org_events, merge_events, events_to_org, format_scheduling

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test-new-functional')

def test_end_to_end_processing():
    """Test that the core functions work together correctly without exact output matching"""
    # Create test input
    existing_content = """* Test Event 1
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            test123
:STATUS:        CONFIRMED
:LOCATION:      Room A
:DURATION:      01:00 hh:mm
:END:
<2025-05-01 Thu 10:00-11:00>

#+begin_agenda
Original description
#+end_agenda

User notes that should be preserved
"""

    new_content = """* Updated Test Event 1
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            test123
:STATUS:        CONFIRMED
:LOCATION:      Room B
:DURATION:      01:30 hh:mm
:END:
<2025-05-01 Thu 10:30-12:00>

Updated description
"""

    # Run the core processing
    existing_events = parse_org_events(existing_content)
    new_events = parse_org_events(new_content)
    merged_events = merge_events(existing_events, new_events)
    result = events_to_org(merged_events, format_dates=True)
    
    logger.debug("Result of processing:\n%s", result)
    
    # Check that key elements were updated properly
    assert "* Updated Test Event 1" in result
    assert "<2025-05-01 Thu 10:30-12:00>" in result
    assert "Room B" in result
    assert "01:30 hh:mm" in result
    assert "#+begin_agenda" in result
    assert "Updated description" in result
    assert "#+end_agenda" in result
    assert "User notes that should be preserved" in result

def test_canceled_events():
    """Test that events missing from new content are marked as canceled"""
    # Create test input with an event that will be canceled
    existing_content = """* Test Event To Cancel
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            cancel123
:STATUS:        CONFIRMED
:LOCATION:      Room A
:DURATION:      01:00 hh:mm
:END:
<2025-05-01 Thu 10:00-11:00>

Original description
"""

    new_content = """* Different Event
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            different456
:STATUS:        CONFIRMED
:LOCATION:      Room B
:DURATION:      01:00 hh:mm
:END:
<2025-05-01 Thu 14:00-15:00>

Some description
"""

    # Run the core processing
    existing_events = parse_org_events(existing_content)
    new_events = parse_org_events(new_content)
    merged_events = merge_events(existing_events, new_events)
    result = events_to_org(merged_events, format_dates=True)
    
    logger.debug("Result of processing:\n%s", result)
    
    # Check that the canceled event is marked correctly
    assert "* CANCELLED: Test Event To Cancel" in result
    assert ":STATUS:        CANCELLED" in result

def test_past_events_preserved():
    """Test that past events are kept as is"""
    # Create test input with a past event
    past_content = """* Past Event
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            past123
:STATUS:        CONFIRMED
:LOCATION:      Room A
:DURATION:      01:00 hh:mm
:END:
<2020-01-01 Wed 10:00-11:00>

Original description
"""

    new_content = """* Updated Past Event
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            past123
:STATUS:        CONFIRMED
:LOCATION:      Room B
:DURATION:      02:00 hh:mm
:END:
<2020-01-01 Wed 09:00-11:00>

Changed description
"""

    # Run the core processing
    past_events = parse_org_events(past_content)
    new_events = parse_org_events(new_content)
    merged_events = merge_events(past_events, new_events)
    result = events_to_org(merged_events, format_dates=True)
    
    logger.debug("Result of processing:\n%s", result)
    
    # Check that the past event is kept as-is
    assert "* Past Event" in result
    assert "<2020-01-01 Wed 10:00-11:00>" in result
    assert "Room A" in result
    assert "01:00 hh:mm" in result

def test_all_day_event_formatting():
    """Test that all-day events are formatted correctly"""
    # Create test input with an all-day event
    all_day_content = """* All Day Event
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            allday123
:STATUS:        CONFIRMED
:LOCATION:      Room A
:DURATION:      1 d 00:00 hh:mm
:ALLDAY:        true
:END:
<2025-05-01 Thu 00:00>--<2025-05-02 Fri 00:00>

All day description
"""

    # Run the core processing
    all_day_events = parse_org_events(all_day_content)
    
    # Extract the scheduling value directly to test the formatting function
    event = all_day_events['allday123']
    scheduling = event['scheduling']
    
    # Test the format_scheduling function directly rather than the full pipeline
    formatted = format_scheduling(scheduling)
    
    # Check that the all-day event is formatted correctly
    assert formatted == "<2025-05-01 Thu>"
    assert "00:00" not in formatted