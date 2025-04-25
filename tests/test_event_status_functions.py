import sys
import os
from datetime import datetime, timedelta

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.sync_calendar import is_past_event, is_cancelled_header, add_cancelled_prefix

def test_is_past_event():
    """Test checking if an event is in the past"""
    # Create a date that's definitely in the past
    past_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    past_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][(datetime.now() - timedelta(days=7)).weekday()]
    
    # Create a date that's definitely in the future
    future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    future_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][(datetime.now() + timedelta(days=7)).weekday()]
    
    # Test with past date
    assert is_past_event(f"<{past_date} {past_day} 09:00-10:00>") == True
    
    # Test with future date
    assert is_past_event(f"<{future_date} {future_day} 09:00-10:00>") == False
    
    # Test with invalid format
    assert is_past_event("Not a date") == False
    
    # Test with None
    assert is_past_event(None) == False

def test_is_cancelled_header():
    """Test checking if a header is already cancelled"""
    # Test with CANCELED prefix
    assert is_cancelled_header("* CANCELED: Event Title") == True
    
    # Test with CANCELLED prefix (British spelling)
    assert is_cancelled_header("* CANCELLED: Event Title") == True
    
    # Test with no cancellation prefix
    assert is_cancelled_header("* Regular Event") == False
    
    # Test with cancellation word in title but not as prefix
    assert is_cancelled_header("* Event about CANCELED meetings") == False

def test_add_cancelled_prefix():
    """Test adding cancelled prefix to headers"""
    # Test adding to regular header
    assert add_cancelled_prefix("* Regular Event") == "* CANCELLED: Regular Event"
    
    # Test not duplicating prefix if already present
    assert add_cancelled_prefix("* CANCELLED: Event") == "* CANCELLED: Event"
    
    # Test with CANCELED spelling (should still use CANCELLED in output)
    assert add_cancelled_prefix("* CANCELED: Event") == "* CANCELED: Event"