from sync_calendar import parse_org_events


def test_parse_simple_event():
    """Test parsing a single simple event"""
    content = """* Simple Event
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            event123
:STATUS:        CONFIRMED
:LOCATION:      Room 101
:END:
<2025-05-01 Thu 09:00-10:00>

This is event content.
"""
    events = parse_org_events(content)

    assert len(events) == 1
    assert "event123" in events

    event = events["event123"]
    assert event.title == "Simple Event"
    assert len(event.properties) == 4  # Without :PROPERTIES: and :END:
    assert event.scheduling == "<2025-05-01 Thu 09:00-10:00>"
    assert event.content == "This is event content."


def test_parse_multiple_events():
    """Test parsing multiple events"""
    content = """* Event One
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            event1
:STATUS:        CONFIRMED
:END:
<2025-05-01 Thu 09:00-10:00>

Content 1

* Event Two
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            event2
:STATUS:        CONFIRMED
:END:
<2025-05-02 Fri 09:00-10:00>

Content 2
"""
    events = parse_org_events(content)

    assert len(events) == 2
    assert "event1" in events
    assert "event2" in events

    assert events["event1"].title == "Event One"
    assert events["event2"].title == "Event Two"


def test_parse_event_with_agenda():
    """Test parsing event with agenda block"""
    content = """* Event With Agenda
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            event123
:STATUS:        CONFIRMED
:END:
<2025-05-01 Thu 09:00-10:00>

#+begin_agenda
Agenda content here
Multiple lines
#+end_agenda

Regular notes
"""
    events = parse_org_events(content)

    assert len(events) == 1
    event = events["event123"]
    assert "#+begin_agenda" in event.content
    assert "Agenda content here" in event.content
    assert "Regular notes" in event.content


def test_parse_cancelled_event():
    """Test parsing a cancelled event"""
    content = """* CANCELLED: Cancelled Event
:PROPERTIES:
:ICAL_EVENT:    t
:ID:            event123
:STATUS:        CANCELLED
:END:
<2025-05-01 Thu 09:00-10:00>

Some content
"""
    events = parse_org_events(content)

    assert len(events) == 1
    event = events["event123"]
    assert event.title == "CANCELLED: Cancelled Event"
    assert event.properties.get("STATUS") == "CANCELLED"
