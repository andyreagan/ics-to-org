import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.sync_calendar import events_to_org, is_all_day_event

def test_events_to_org_sorting():
    """Test that events are sorted by date/time"""
    events = {
        'event3': {
            'header': '* Event 3',
            'properties': [':PROPERTIES:', ':ID:            event3', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-03 Sat 09:00-10:00>',
            'content': 'Event 3 content'
        },
        'event1': {
            'header': '* Event 1',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': 'Event 1 content'
        },
        'event2': {
            'header': '* Event 2',
            'properties': [':PROPERTIES:', ':ID:            event2', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-02 Fri 09:00-10:00>',
            'content': 'Event 2 content'
        }
    }
    
    result = events_to_org(events)
    
    # The result should have the events in chronological order
    lines = result.split('\n')
    event1_index = next((i for i, line in enumerate(lines) if '* Event 1' in line), -1)
    event2_index = next((i for i, line in enumerate(lines) if '* Event 2' in line), -1)
    event3_index = next((i for i, line in enumerate(lines) if '* Event 3' in line), -1)
    
    assert event1_index < event2_index < event3_index, "Events should be sorted chronologically"

def test_events_to_org_format_dates():
    """Test that all-day events have their dates formatted correctly"""
    events = {
        'event1': {
            'header': '* All Day Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':ALLDAY:        true', ':END:'],
            'scheduling': '<2025-05-01 Thu 00:00>--<2025-05-02 Fri 00:00>',
            'content': 'All day event content'
        }
    }
    
    # With formatting enabled
    result_with_formatting = events_to_org(events, format_dates=True)
    assert '<2025-05-01 Thu>' in result_with_formatting
    assert '00:00' not in result_with_formatting
    
    # With formatting disabled
    result_without_formatting = events_to_org(events, format_dates=False)
    assert '<2025-05-01 Thu 00:00>--<2025-05-02 Fri 00:00>' in result_without_formatting

def test_events_to_org_multiday_formatting():
    """Test that multi-day events have their dates formatted correctly"""
    events = {
        'event1': {
            'header': '* Multi Day Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':ALLDAY:        true', ':END:'],
            'scheduling': '<2025-05-01 Thu 00:00>--<2025-05-03 Sat 00:00>',
            'content': 'Multi day event content'
        }
    }
    
    # With formatting enabled
    result = events_to_org(events, format_dates=True)
    assert '<2025-05-01 Thu>--<2025-05-02 Fri>' in result
    assert '00:00' not in result

def test_events_to_org_blank_lines():
    """Test that appropriate blank lines are inserted between events"""
    events = {
        'event1': {
            'header': '* Event 1',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': 'Event 1 content'
        },
        'event2': {
            'header': '* Event 2',
            'properties': [':PROPERTIES:', ':ID:            event2', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-02 Fri 09:00-10:00>',
            'content': 'Event 2 content'
        }
    }
    
    result = events_to_org(events)
    lines = result.split('\n')
    
    # Find the end of the first event and beginning of the second
    event1_content_index = next((i for i, line in enumerate(lines) if 'Event 1 content' in line), -1)
    event2_header_index = next((i for i, line in enumerate(lines) if '* Event 2' in line), -1)
    
    # There should be exactly two blank lines between events
    assert event2_header_index - event1_content_index == 3, "There should be exactly two blank lines between events"

def test_events_to_org_empty_content():
    """Test handling of events with empty content"""
    events = {
        'event1': {
            'header': '* Event With Empty Content',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': ''
        }
    }
    
    result = events_to_org(events)
    
    # Check that the event is included even with empty content
    assert '* Event With Empty Content' in result
    # After the scheduling line, there should not be additional empty lines
    lines = result.split('\n')
    scheduling_index = next((i for i, line in enumerate(lines) if '<2025-05-01 Thu 09:00-10:00>' in line), -1)
    
    # The rest of the output should be minimal without extra blank lines
    assert scheduling_index > 0, "Scheduling line should be present"