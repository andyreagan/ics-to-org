#!/usr/bin/env python3
"""Direct ICS to Org-mode synchronization without intermediate tools."""

import argparse
import gzip
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from icalendar import Calendar, Event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ics-sync")


@dataclass
class OrgEvent:
    """Simplified event model for org-mode."""

    uid: str  # Unique identifier from ICS
    summary: str  # Event title
    start: datetime
    end: datetime | None
    location: str | None
    description: str | None  # From ICS
    status: str  # CONFIRMED, TENTATIVE, CANCELLED
    categories: str | None

    # Org-specific
    user_notes: str = ""  # User's personal notes

    @property
    def is_all_day(self) -> bool:
        """Check if this is an all-day event."""
        return self.end is None or (self.end - self.start).days >= 1

    def to_org_timestamp(self) -> str:
        """Convert to org-mode timestamp format."""
        if self.is_all_day:
            return f"<{self.start.strftime('%Y-%m-%d %a')}>"
        elif self.end:
            return f"<{self.start.strftime('%Y-%m-%d %a %H:%M')}-{self.end.strftime('%H:%M')}>"
        else:
            return f"<{self.start.strftime('%Y-%m-%d %a %H:%M')}>"

    def to_org(self) -> str:
        """Convert to org-mode format."""
        lines = []

        # Header with title
        title = self.summary
        if self.status == "CANCELLED":
            title = f"CANCELLED: {title}"
        lines.append(f"* {title}")

        # Properties drawer
        lines.append(":PROPERTIES:")
        lines.append(f":UID:           {self.uid}")
        if self.location:
            lines.append(f":LOCATION:      {self.location}")
        if self.description:
            # Escape newlines in description
            desc = self.description.replace("\n", "\\n")
            lines.append(f":DESCRIPTION:   {desc}")
        lines.append(f":STATUS:        {self.status}")
        if self.categories:
            lines.append(f":CATEGORIES:    {self.categories}")
        lines.append(":END:")

        # Timestamp
        lines.append(self.to_org_timestamp())

        # User notes (if any)
        if self.user_notes:
            lines.append("")
            lines.append(self.user_notes)

        return "\n".join(lines)


def parse_ics_event(component: Event, default_timezone: str | None = None) -> OrgEvent | None:
    """Parse an ICS VEVENT component into an OrgEvent."""
    try:
        # Extract UID
        uid = str(component.get("UID", ""))
        if not uid:
            logger.warning("Event missing UID, skipping")
            return None

        # Extract summary (title)
        summary = str(component.get("SUMMARY", "Untitled Event"))

        # Extract dates
        dtstart = component.get("DTSTART")
        if dtstart:
            start = dtstart.dt
            if not isinstance(start, datetime):
                # Convert date to datetime for all-day events
                start = datetime.combine(start, datetime.min.time())
            elif hasattr(start, "tzinfo") and start.tzinfo is not None:
                # Convert timezone-aware to naive datetime
                start = start.replace(tzinfo=None)
        else:
            logger.warning(f"Event {uid} missing start date, skipping")
            return None

        dtend = component.get("DTEND")
        end = None
        if dtend:
            end = dtend.dt
            if not isinstance(end, datetime):
                end = datetime.combine(end, datetime.min.time())
            elif hasattr(end, "tzinfo") and end.tzinfo is not None:
                # Convert timezone-aware to naive datetime
                end = end.replace(tzinfo=None)

        # Extract other fields
        location = str(component.get("LOCATION", "")) or None
        description = str(component.get("DESCRIPTION", "")) or None
        status = str(component.get("STATUS", "CONFIRMED"))

        # Handle categories (can be a complex object)
        categories_obj = component.get("CATEGORIES")
        if categories_obj:
            if hasattr(categories_obj, "to_ical"):
                categories = categories_obj.to_ical().decode("utf-8")
            else:
                categories = str(categories_obj)
        else:
            categories = None

        return OrgEvent(
            uid=uid,
            summary=summary,
            start=start,
            end=end,
            location=location,
            description=description,
            status=status,
            categories=categories,
        )
    except Exception as e:
        logger.error(f"Error parsing event: {e}")
        return None


def fetch_ics(url: str) -> Calendar:
    """Fetch and parse ICS file from URL or local file path."""
    logger.info(f"Fetching calendar from {url}")

    # Handle local file URLs and paths
    if url.startswith("file://") or not url.startswith(("http://", "https://")):
        file_path = url.replace("file://", "") if url.startswith("file://") else url
        logger.info(f"Reading local file: {file_path}")
        try:
            with open(file_path, "rb") as f:
                ics_data = f.read()
            logger.info(f"Read {len(ics_data)} bytes from local file")
        except FileNotFoundError:
            logger.error(f"Local file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading local file: {e}")
            raise
    else:
        # Handle HTTP/HTTPS URLs with proper headers for Outlook/Office365
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/calendar,application/calendar+xml,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, identity",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        request = Request(url, headers=headers)

        try:
            with urlopen(request, timeout=30) as response:
                # Check if we got HTML instead of ICS (common with auth issues)
                content_type = response.headers.get("content-type", "").lower()
                content_encoding = response.headers.get("content-encoding", "").lower()
                logger.debug(f"Response content-type: {content_type}")
                logger.debug(f"Response content-encoding: {content_encoding}")
                logger.debug(f"Response headers: {dict(response.headers)}")

                ics_data = response.read()

                # Check if response looks like HTML (redirect page)
                if ics_data.startswith(b"<!DOCTYPE") or ics_data.startswith(b"<html"):
                    logger.error("Received HTML response instead of ICS data")
                    logger.error("This usually means:")
                    logger.error("1. The calendar URL requires authentication")
                    logger.error("2. The calendar is private and needs to be made public")
                    logger.error("3. The URL has expired or is incorrect")
                    logger.error(
                        f"Response starts with: {ics_data[:200].decode('utf-8', errors='ignore')}"
                    )
                    raise ValueError("Received HTML redirect page instead of calendar data")

                # Log some basic info about what we received
                logger.debug(f"Received {len(ics_data)} bytes of data")
                logger.debug(f"First 100 chars: {ics_data[:100].decode('utf-8', errors='ignore')}")

        except HTTPError as e:
            logger.error(f"HTTP Error {e.code}: {e.reason}")
            if e.code == 401:
                logger.error("Authentication required - calendar may be private")
            elif e.code == 403:
                logger.error("Access forbidden - calendar may be private or URL expired")
            elif e.code == 404:
                logger.error("Calendar not found - check the URL")
            raise
        except URLError as e:
            logger.error(f"URL Error: {e.reason}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching calendar: {e}")
            raise

    # Try to decompress if the data appears to be compressed
    original_data = ics_data
    try:
        # Check if data looks like it might be gzipped (starts with gzip magic bytes)
        if ics_data.startswith(b"\x1f\x8b"):
            logger.info("Detected gzip compression, decompressing...")
            ics_data = gzip.decompress(ics_data)
        # Or if it contains binary garbage and doesn't start with BEGIN:VCALENDAR
        elif not ics_data.startswith(b"BEGIN:VCALENDAR") and len(ics_data) > 100:
            # Try gzip decompression as a fallback
            try:
                logger.info("Data doesn't look like ICS, trying gzip decompression...")
                ics_data = gzip.decompress(ics_data)
            except Exception:
                # If gzip fails, try raw deflate
                try:
                    import zlib

                    logger.info("Gzip failed, trying deflate decompression...")
                    ics_data = zlib.decompress(ics_data)
                except Exception:
                    # If both fail, use original data
                    ics_data = original_data
    except Exception as e:
        logger.warning(f"Decompression failed: {e}, using original data")
        ics_data = original_data

    try:
        cal = Calendar.from_ical(ics_data)
        logger.info("Successfully parsed ICS calendar")
        return cal
    except Exception as e:
        logger.error(f"Error parsing ICS data: {e}")
        # Show both original and potentially decompressed data info
        logger.error(f"Original data length: {len(original_data)} bytes")
        logger.error(f"Final data length: {len(ics_data)} bytes")
        logger.error(f"Data starts with: {ics_data[:200].decode('utf-8', errors='ignore')}")

        # If data looks binary, give helpful message
        if b"\x00" in ics_data[:100] or len([b for b in ics_data[:100] if b > 127]) > 10:
            logger.error("Data appears to be binary/compressed. Try:")
            logger.error("1. Right-click the calendar URL in browser and 'Save as...'")
            logger.error("2. Make sure you're using the ICS URL, not the web calendar URL")
            logger.error("3. Check if the file was downloaded correctly")
        raise


def parse_ics_calendar(
    cal: Calendar, days_forward: int = 30, days_backward: int = 7
) -> dict[str, OrgEvent]:
    """Parse ICS calendar into OrgEvents within date range."""
    events = {}

    # Calculate date range
    now = datetime.now()
    start_date = now - timedelta(days=days_backward)
    end_date = now + timedelta(days=days_forward)

    for component in cal.walk():
        if component.name == "VEVENT":
            event = parse_ics_event(component)
            if event:
                # Check if event is in date range (handle timezone awareness)
                event_start = event.start
                if hasattr(event_start, "tzinfo") and event_start.tzinfo is not None:
                    # Convert to naive datetime for comparison
                    event_start = event_start.replace(tzinfo=None)

                if start_date <= event_start <= end_date:
                    events[event.uid] = event
                    logger.debug(f"Parsed event: {event.summary} on {event.start}")

    logger.info(f"Parsed {len(events)} events within date range")
    return events


def parse_org_file(filepath: str) -> dict[str, OrgEvent]:
    """Parse existing org file to extract events and user notes."""
    events: dict[str, OrgEvent] = {}

    try:
        with open(filepath) as f:
            content = f.read()
    except FileNotFoundError:
        logger.info(f"Org file {filepath} not found, will create new")
        return events

    # Split into events (each starts with "* ")
    event_blocks = re.split(r"^(?=\* )", content, flags=re.MULTILINE)

    for block in event_blocks:
        if not block.strip():
            continue

        # Parse the event block
        lines = block.strip().split("\n")
        if not lines[0].startswith("* "):
            continue

        # Extract title
        title = lines[0][2:].strip()

        # Find properties drawer
        uid = None
        properties = {}
        prop_start = None
        prop_end = None

        for i, line in enumerate(lines[1:], 1):
            if line.strip() == ":PROPERTIES:":
                prop_start = i
            elif line.strip() == ":END:" and prop_start is not None:
                prop_end = i
                break

        if prop_start and prop_end:
            for line in lines[prop_start + 1 : prop_end]:
                match = re.match(r":(\w+):\s+(.*)", line)
                if match:
                    key, value = match.groups()
                    properties[key] = value.strip()
                    if key == "UID":
                        uid = value.strip()

        if not uid:
            continue  # Skip events without UID

        # Find timestamp
        timestamp_line = None
        for i in range(prop_end + 1 if prop_end else 1, len(lines)):
            if re.match(r"<\d{4}-\d{2}-\d{2}", lines[i].strip()):
                timestamp_line = i
                break

        # Extract user notes (everything after timestamp)
        user_notes = ""
        if timestamp_line and timestamp_line + 1 < len(lines):
            user_notes = "\n".join(lines[timestamp_line + 1 :]).strip()

        # Parse timestamp to get start/end times
        start = datetime.now()  # Default, will be overridden by merge
        end = None

        # Create event (minimal parsing, will be updated from ICS)
        events[uid] = OrgEvent(
            uid=uid,
            summary=title.replace("CANCELLED: ", ""),  # Remove prefix if present
            start=start,
            end=end,
            location=properties.get("LOCATION"),
            description=properties.get("DESCRIPTION"),
            status=properties.get("STATUS", "CONFIRMED"),
            categories=properties.get("CATEGORIES"),
            user_notes=user_notes,
        )

        logger.debug(f"Parsed existing event: {title} (UID: {uid})")

    logger.info(f"Parsed {len(events)} existing events from org file")
    return events


def merge_events(existing: dict[str, OrgEvent], new: dict[str, OrgEvent]) -> dict[str, OrgEvent]:
    """Merge new ICS events with existing org events."""
    merged = {}

    # Process all new events
    for uid, new_event in new.items():
        if uid in existing:
            # Update existing event with new data, preserve user notes
            old_event = existing[uid]
            new_event.user_notes = old_event.user_notes
            merged[uid] = new_event
            logger.debug(f"Updated event: {new_event.summary}")
        else:
            # Brand new event
            merged[uid] = new_event
            logger.debug(f"Added new event: {new_event.summary}")

    # Mark removed events as cancelled
    for uid, old_event in existing.items():
        if uid not in new:
            old_event.status = "CANCELLED"
            merged[uid] = old_event
            logger.debug(f"Marked as cancelled: {old_event.summary}")

    return merged


def write_org_file(events: dict[str, OrgEvent], filepath: str) -> None:
    """Write events to org file."""
    # Sort events by start date
    sorted_events = sorted(events.values(), key=lambda e: e.start)

    # Group by date for better organization
    content: list[str] = []
    current_date = None

    for event in sorted_events:
        event_date = event.start.date()

        # Add date separator
        if current_date != event_date:
            if content:  # Add spacing between dates
                content.append("")
            content.append(f"# {event_date.strftime('%A, %B %d, %Y')}")
            content.append("")
            current_date = event_date

        content.append(event.to_org())
        content.append("")

    # Write to file
    with open(filepath, "w") as f:
        f.write("\n".join(content))

    logger.info(f"Wrote {len(events)} events to {filepath}")


def sync_calendar(
    ics_url: str, org_file: str, days_forward: int = 30, days_backward: int = 7
) -> None:
    """Main sync function."""
    logger.info("Starting calendar sync")

    # Fetch and parse ICS
    cal = fetch_ics(ics_url)
    new_events = parse_ics_calendar(cal, days_forward, days_backward)

    # Parse existing org file
    existing_events = parse_org_file(org_file)

    # Merge events
    merged_events = merge_events(existing_events, new_events)

    # Write back to org file
    write_org_file(merged_events, org_file)

    logger.info("Sync completed successfully")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync ICS calendar to org-mode file, preserving user notes",
        epilog="""
Troubleshooting Outlook/Office365 calendars:
1. Make sure your calendar is set to "Public" in Outlook settings
2. Use the direct ICS URL from calendar settings, not the web view URL
3. Try running with --debug to see detailed error messages
4. If you get HTML instead of calendar data, the URL may require authentication
        """,
    )
    parser.add_argument("--ics-url", required=True, help="ICS calendar URL or local file path")
    parser.add_argument("--org-file", required=True, help="Org file path")
    parser.add_argument(
        "--days-forward", type=int, default=30, help="Days to look forward (default: 30)"
    )
    parser.add_argument(
        "--days-backward", type=int, default=7, help="Days to look backward (default: 7)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        sync_calendar(args.ics_url, args.org_file, args.days_forward, args.days_backward)
    except ValueError as e:
        if "HTML redirect page" in str(e):
            logger.error("\n" + "=" * 60)
            logger.error("OUTLOOK CALENDAR TROUBLESHOOTING:")
            logger.error("=" * 60)
            logger.error(
                "Your Outlook calendar URL is returning a login page instead of calendar data."
            )
            logger.error("\nTo fix this:")
            logger.error("1. Go to Outlook Web (outlook.office365.com)")
            logger.error("2. Open your calendar")
            logger.error("3. Click 'Add calendar' > 'From internet'")
            logger.error("4. Right-click your calendar name > 'Settings and sharing'")
            logger.error("5. Under 'Publish a calendar', click 'Publish'")
            logger.error("6. Set permissions to 'Can view all details'")
            logger.error("7. Copy the ICS link (ends with .ics)")
            logger.error("\nAlternatively, try downloading the .ics file manually")
            logger.error(
                "and use: ics-sync --ics-url file:///path/to/calendar.ics --org-file events.org"
            )
        logger.error(f"Sync failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
