from datetime import datetime, timedelta

from sync_calendar import is_past_event, is_cancelled_title, add_cancelled_prefix


def test_is_past_event():
    """Test checking if an event is in the past"""
    # Create a date that's definitely in the past
    past_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    past_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
        (datetime.now() - timedelta(days=7)).weekday()
    ]

    # Create a date that's definitely in the future
    future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    future_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
        (datetime.now() + timedelta(days=7)).weekday()
    ]

    # Test with past date
    assert is_past_event(f"<{past_date} {past_day} 09:00-10:00>")

    # Test with future date
    assert not is_past_event(f"<{future_date} {future_day} 09:00-10:00>")

    # Test with past date but within days_backward window
    past_5_days = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    past_5_day = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
        (datetime.now() - timedelta(days=5)).weekday()
    ]
    assert is_past_event(
        f"<{past_5_days} {past_5_day} 09:00-10:00>", days_backward=0
    )  # Is past with 0 days
    assert not is_past_event(
        f"<{past_5_days} {past_5_day} 09:00-10:00>", days_backward=7
    )  # Not past with 7 days

    # Test with invalid format
    assert not is_past_event("Not a date")


def test_is_cancelled_title():
    """Test checking if a title is already cancelled"""
    # Test with CANCELED prefix
    assert is_cancelled_title("CANCELED: Event Title")

    # Test with CANCELLED prefix (British spelling)
    assert is_cancelled_title("CANCELLED: Event Title")

    # Test with no cancellation prefix
    assert not is_cancelled_title("Regular Event")

    # Test with cancellation word in title but not as prefix
    assert not is_cancelled_title("Event about CANCELED meetings")


def test_add_cancelled_prefix():
    """Test adding cancelled prefix to titles"""
    # Test adding to regular title
    assert add_cancelled_prefix("Regular Event") == "CANCELLED: Regular Event"

    # Test not duplicating prefix if already present
    assert add_cancelled_prefix("CANCELLED: Event") == "CANCELLED: Event"

    # Test with CANCELED spelling (should still use CANCELLED in output)
    assert add_cancelled_prefix("CANCELED: Event") == "CANCELED: Event"
