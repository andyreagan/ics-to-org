import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.sync_calendar import is_all_day_event, format_scheduling

def test_is_all_day_event():
    # Test one-day event
    assert is_all_day_event('<2025-04-27 Sun 00:00>--<2025-04-28 Mon 00:00>', []) == True
    
    # Test multi-day event
    assert is_all_day_event('<2025-04-27 Sun 00:00>--<2025-04-29 Tue 00:00>', []) == True

    # Test an event that has actual hours
    assert is_all_day_event('<2025-04-27 Sun 01:00>--<2025-04-29 Tue 03:00>', []) == False
    
    # There is no "ALLDAY" property
    assert is_all_day_event('', [':ALLDAY:        true']) == False
    
    # Can't rely on the length
    assert is_all_day_event('', [':DURATION:      1 d 00:00 hh:mm']) == False
    
    # Test regular event (not all-day)
    assert is_all_day_event('<2025-04-27 Sun 10:00-11:00>', []) == False
    
    # Test regular event with properties (not all-day)
    assert is_all_day_event('<2025-04-27 Sun 10:00-11:00>', [':DURATION:      01:00 hh:mm']) == False

def test_format_scheduling():
    # Test one-day all-day event (Sun 00:00 to Mon 00:00 is just Sunday)
    assert format_scheduling('<2025-04-27 Sun 00:00>--<2025-04-28 Mon 00:00>') == '<2025-04-27 Sun>'
    assert format_scheduling('<2025-04-28 Mon 00:00>--<2025-04-29 Tue 00:00>') == '<2025-04-28 Mon>'
    assert format_scheduling('<2025-04-29 Tue 00:00>--<2025-04-30 Wed 00:00>') == '<2025-04-29 Tue>'
    
    # Test multi-day all-day event
    # This test case comes from the expected output in the integration test
    result = format_scheduling('<2025-04-27 Sun 00:00>--<2025-04-29 Tue 00:00>')
    assert result == '<2025-04-27 Sun>--<2025-04-28 Mon>', f"Failed: got {result} instead"

    result = format_scheduling('<2025-04-27 Sun 00:00>--<2025-04-30 Wed 00:00>')
    assert result == '<2025-04-27 Sun>--<2025-04-29 Tue>', f"Failed: got {result} instead"    
    
    # Test already formatted multi-day event
    assert format_scheduling('<2025-04-27 Sun>--<2025-04-28 Mon>') == '<2025-04-27 Sun>--<2025-04-28 Mon>'
    
    # Test regular event (not all-day)
    assert format_scheduling('<2025-04-27 Sun 10:00-11:00>') == '<2025-04-27 Sun 10:00-11:00>'

if __name__ == "__main__":
    test_is_all_day_event()
    test_format_scheduling()
    print("All tests passed!")
