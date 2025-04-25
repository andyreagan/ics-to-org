import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.sync_calendar import merge_events

def test_merge_new_event():
    """Test merging a new event that doesn't exist in existing events"""
    existing_events = {}
    
    new_events = {
        'event1': {
            'header': '* New Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': 'New event content'
        }
    }
    
    merged = merge_events(existing_events, new_events)
    
    assert len(merged) == 1
    assert 'event1' in merged
    assert merged['event1']['header'] == '* New Event'
    assert '#+begin_agenda' in merged['event1']['content']
    assert 'New event content' in merged['event1']['content']

def test_merge_updated_event():
    """Test merging an event that exists in both with updates"""
    existing_events = {
        'event1': {
            'header': '* Existing Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':LOCATION:      Room A', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': '#+begin_agenda\nOld content\n#+end_agenda\n\nUser notes'
        }
    }
    
    new_events = {
        'event1': {
            'header': '* Updated Event',  # Title changed
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':LOCATION:      Room B', ':END:'],  # Location changed
            'scheduling': '<2025-05-01 Thu 10:00-11:00>',  # Time changed
            'content': 'Updated content'
        }
    }
    
    merged = merge_events(existing_events, new_events)
    
    assert len(merged) == 1
    assert merged['event1']['header'] == '* Updated Event'  # Should use new header
    assert ':LOCATION:      Room B' in merged['event1']['properties']  # Should use new properties
    assert merged['event1']['scheduling'] == '<2025-05-01 Thu 10:00-11:00>'  # Should use new scheduling
    assert 'Updated content' in merged['event1']['content']  # Should update agenda
    assert 'User notes' in merged['event1']['content']  # Should preserve user notes

def test_mark_canceled_events():
    """Test that events no longer in calendar are marked as canceled"""
    existing_events = {
        'event1': {
            'header': '* Existing Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': 'Event content'
        }
    }
    
    new_events = {}  # Event no longer in calendar
    
    merged = merge_events(existing_events, new_events)
    
    assert len(merged) == 1
    assert merged['event1']['header'] == '* CANCELLED: Existing Event'
    assert any(':STATUS:        CANCELLED' in prop for prop in merged['event1']['properties'])

def test_preserve_past_events():
    """Test that past events are preserved as-is"""
    # Create a past event
    past_event = {
        'event1': {
            'header': '* Past Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2023-01-01 Sun 09:00-10:00>',  # Past date
            'content': 'Past event content'
        }
    }
    
    # New version of the event with changes
    new_events = {
        'event1': {
            'header': '* Updated Past Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':LOCATION:      New Room', ':END:'],
            'scheduling': '<2023-01-01 Sun 10:00-11:00>',
            'content': 'Updated content'
        }
    }
    
    merged = merge_events(past_event, new_events)
    
    assert len(merged) == 1
    # Past event should be preserved as-is
    assert merged['event1']['header'] == '* Past Event'
    assert ':LOCATION:      New Room' not in str(merged['event1']['properties'])
    assert merged['event1']['scheduling'] == '<2023-01-01 Sun 09:00-10:00>'
    assert merged['event1']['content'] == 'Past event content'

def test_agenda_block_creation():
    """Test that agenda blocks are properly created for new events"""
    new_events = {
        'event1': {
            'header': '* New Event',
            'properties': [':PROPERTIES:', ':ID:            event1', ':STATUS:        CONFIRMED', ':END:'],
            'scheduling': '<2025-05-01 Thu 09:00-10:00>',
            'content': 'Description text'
        }
    }
    
    merged = merge_events({}, new_events)
    
    assert '#+begin_agenda\nDescription text\n#+end_agenda' in merged['event1']['content']