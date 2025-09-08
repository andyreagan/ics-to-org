# ics-to-org

<a href="https://github.com/andyreagan/ics-to-org/actions/workflows/python-test-publish.yml"><img src="https://github.com/andyreagan/ics-to-org/actions/workflows/python-test-publish.yml/badge.svg" alt="Tests"></a> <a href="https://badge.fury.io/py/ics-to-org"><img src="https://badge.fury.io/py/ics-to-org.svg" alt="PyPI version"></a>

Sync iCalendar events to org-mode files while preserving your notes.

## What's New in v1.0.0

This is a ****major rewrite**** with significantly improved reliability and simplicity:

- ✅ ****No more Node.js dependency**** - Pure Python implementation using the `icalendar` library
- ✅ ****Cleaner org format**** - ICS descriptions stored in `:DESCRIPTION:` property, user notes go directly in the event body
- ✅ ****Bulletproof merge logic**** - Calendar data always updates, user notes always preserved
- ✅ ****Better timezone handling**** - Proper handling of UTC and all-day events
- ✅ ****Comprehensive tests**** - Real .ics files and .org examples with full integration testing

## Installation

Simple single-step installation:

``` bash
pip install ics-to-org
```

Or with uv:

``` bash
uv tool add ics-to-org
```

## Usage

After installation, you can run the tool:

``` bash
ics-sync --ics-url "https://outlook.office365.com/..." \
         --org-file "meetings.org" \
         --days-forward 30 \
         --days-backward 7
```

Or run it directly with `uvx` (no installation needed):

``` bash
uvx --from ics-to-org ics-sync --ics-url "https://calendar.google.com/calendar/ical/..." \
                                  --org-file "calendar.org"
```

Command-line options:

| Option         | Description                               | Default |
|----------------|-------------------------------------------|---------|
| –ics-url       | URL of the iCalendar feed (required)      | \-      |
| –org-file      | Path to the org file to update (required) | \-      |
| –days-forward  | Number of days forward to fetch           | 30      |
| –days-backward | Number of days backward to fetch          | 7       |
| –debug         | Enable debug logging                      | false   |

## How It Works

The sync process:

1.  ****Fetches**** your calendar from the ICS URL
2.  ****Parses**** your existing org file to extract user notes
3.  ****Merges**** calendar updates with your preserved notes:
    - Calendar data (title, time, location, description) always gets updated
    - Your personal notes are always preserved
    - Removed events are marked as `CANCELLED:` but kept with your notes
    - New events are added cleanly
4.  ****Writes**** the updated org file with events sorted by date

## Org File Format

Events are stored in a clean, standard org format:

``` org
* Team Meeting
:PROPERTIES:
:UID:           meeting123@company.com
:LOCATION:      Conference Room A
:DESCRIPTION:   Weekly team sync and project updates
:STATUS:        CONFIRMED
:CATEGORIES:    Work
:END:
<2025-01-15 Wed 14:00-15:00>

My personal notes for the meeting:
- Remember to bring the quarterly report
- Ask about the new project timeline
- Discuss vacation schedule

Action items:
- [ ] Finish the client proposal
- [X] Review the budget numbers
```

Key features of the format:

- `:DESCRIPTION:` contains the calendar description (read-only)
- `:UID:` provides the unique identifier for syncing
- Event body contains your personal notes in any format (markdown, org-mode, plain text)
- All-day events show as `<2025-01-20 Mon>`
- Timed events show as `<2025-01-15 Wed 14:00-15:00>`

## Examples

### Basic sync with default settings

``` bash
ics-sync --ics-url "https://calendar.google.com/calendar/ical/..." \
         --org-file "calendar.org"
```

### Longer time range with debug output

``` bash
ics-sync --ics-url "https://outlook.office365.com/owa/calendar/..." \
         --org-file "work-calendar.org" \
         --days-forward 60 \
         --days-backward 14 \
         --debug
```

### Using with uvx (no installation required)

``` bash
# Run directly from PyPI without installing
uvx --from ics-to-org ics-sync --ics-url "https://example.com/calendar.ics" \
                                  --org-file "my-calendar.org" \
                                  --days-forward 60 \
                                  --debug
```

### Using with uv run (in a project)

``` bash
uv run ics-sync --ics-url "https://example.com/calendar.ics" \
                --org-file "my-calendar.org"
```

### Using with local .ics files

If you can't access the calendar URL directly (common with Outlook), download the .ics file and use it locally:

``` bash
# Using a local file path
ics-sync --ics-url "/path/to/downloaded/calendar.ics" \
         --org-file "calendar.org"

# Or with file:// URL
ics-sync --ics-url "file:///path/to/calendar.ics" \
         --org-file "calendar.org"
```

## Troubleshooting

### Outlook/Office365 Calendar Issues

If you're having trouble accessing your Outlook calendar:

1.  ****Download the .ics file manually****: Go to Outlook Web → Calendar → Share → Publish Calendar → Copy the ICS URL → Download it with your browser
2.  ****Use the downloaded file****: `ics-sync --ics-url "/path/to/calendar.ics" --org-file "events.org"`
3.  ****Check calendar permissions****: Make sure your calendar is set to "Public" with "Can view all details" in Outlook settings
4.  ****Try the debug flag****: Run with `--debug` to see detailed error messages

### Common Error Messages

- \***"Received HTML response instead of ICS data"\***: The calendar URL requires authentication or is private
- \***"Authentication required"\***: Calendar is not publicly accessible
- \***"Object moved to here"\***: Calendar URL has redirects/authentication issues

For these issues, downloading the .ics file manually is the most reliable solution.

## Testing

The project includes comprehensive tests with realistic examples:

``` bash
pytest tests/ -v
```

Test coverage includes:

- ✅ ****Unit tests**** for all core functions
- ✅ ****Integration tests**** with real .ics files and .org files
- ✅ ****Edge cases**** like timezone handling, malformed events, empty calendars
- ✅ ****User note preservation**** across various markdown and org-mode formats
- ✅ ****Complete workflows**** from ICS fetch through merge to org file output

## Migration from v0.x

If you're upgrading from the old version:

1.  ****Remove the icsorg dependency****: `npm uninstall -g icsorg`
2.  ****Update your scripts****: Remove `--author` and `--email` parameters (no longer needed)
3.  ****Review your org files****: The new format stores descriptions in properties instead of agenda blocks

The new format is cleaner and more reliable, but you may want to manually clean up old agenda blocks if desired.

## Development

``` bash
# Clone the repository
git clone https://github.com/andyreagan/ics-to-org
cd ics-to-org

# Install with uv (recommended)
uv sync

# Run tests
uv run pytest

# Build package
uv build
```

## Contributing

Contributions are welcome! Please:

1.  Add tests for any new functionality
2.  Ensure all tests pass: `uv run pytest`
3.  Follow the existing code style
4.  Update documentation as needed

## License

MIT License. See LICENSE file for details.
