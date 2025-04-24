# ics-to-org

[![Tests](https://github.com/andyreagan/ics-to-org/actions/workflows/python-test-publish.yml/badge.svg)](https://github.com/andyreagan/ics-to-org/actions/workflows/python-test-publish.yml)
[![PyPI version](https://badge.fury.io/py/ics-to-org.svg)](https://badge.fury.io/py/ics-to-org)

## ics-to-org

Sync iCalendar events to org-mode files while preserving your notes.

### Installation

This tool requires both the Python package and the icsorg npm package:

1. Install the icsorg npm package:

```bash
npm install -g icsorg
```

2. Install the Python package:

```bash
pip install ics-to-org
```

### Usage

After installation, you can use the command-line tool:

```bash
sync_calendar --ics-url "https://outlook.office365.com/..." \
              --org-file "meetings.org" \
              --author "Your Name" \
              --email "your.email@example.com"
```


This script will:

- Fetch the latest calendar data using icsorg
- For each event in your calendar:
  - Update the header, properties, and scheduling from the calendar
  - If the event has a description in the calendar, update the #+begin_agenda #+end_agenda block
  - Preserve any notes you've made outside of the agenda block
- For events that are no longer in your calendar, mark them as "CANCELED" but keep them in your file
- Sort all events by their scheduled time

### Testing

These test files cover several important scenarios:

- Meeting with updated title, time, and description
  - Original: "Review WellAdmin/TradV Feed and discuss policy year field"
  - Updated: "UPDATED: Review WellAdmin/TradV Feed Implementation"
  - Time changed from 14:30-15:00 to 14:00-15:00
  - Description updated with more details
  - Your notes are preserved
- Meeting that remains unchanged
  - "Weekly Team Sync" stays the same
  - Your notes are preserved
- New meeting added
  - "New Project Kickoff Meeting" appears in the updated calendar
  - Creates an agenda block from the description
- Meeting that was canceled
  - "Past Meeting That Got Canceled" is no longer in the calendar
  - Marked as "CANCELED" in the org file
  - Your notes are preserved

*How to Use These Test Files*

```
python -m pytest
```

If the test passes, you're good to go! If not, the diff output will show what's
different between the expected and actual output.

These test files should help you verify that the sync script correctly handles
all the scenarios you described, including:

- Updating meeting properties (title, time, location)
- Updating agenda blocks
- Preserving your notes
- Handling canceled meetings
- Adding new meetings