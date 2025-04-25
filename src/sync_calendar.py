#!/usr/bin/env python3
import subprocess
import re
import os
import tempfile
import logging
from datetime import datetime, timedelta
import argparse
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ics-to-org')

def run_icsorg(ics_url, output_file, author, email):
    """Run icsorg to get latest calendar data"""
    cmd = [
        "npx", "icsorg", 
        "-a", author, 
        "-e", email,
        "-f", "7",  # fetch 7 days
        "-p", "0",  # include past 0 days
        "-i", ics_url,
        "-o", output_file
    ]
    subprocess.run(cmd, check=True)

def parse_org_events(content):
    """Parse org-mode content into events dictionary"""
    logger.debug("Parsing org events content with length: %d", len(content))
    events = {}
    lines = content.split('\n')
    
    current_event = None
    current_content = []
    in_properties = False
    
    for line in lines:
        if line.startswith('* '):
            # Save previous event if exists
            if current_event:
                events[current_event['id']] = {
                    'header': current_event['header'],
                    'properties': current_event['properties'],
                    'scheduling': current_event['scheduling'],
                    'content': '\n'.join(current_content)
                }
            
            # Start new event
            current_event = {
                'id': None,
                'header': line,
                'properties': [],
                'scheduling': None,
                'content': []
            }
            current_content = []
            in_properties = False
            
        elif current_event:
            if line == ':PROPERTIES:':
                in_properties = True
                current_event['properties'].append(line)
            elif line == ':END:':
                in_properties = False
                current_event['properties'].append(line)
            elif in_properties:
                current_event['properties'].append(line)
                # Extract the ID
                if line.strip().startswith(':ID:'):
                    current_event['id'] = line.split(':ID:')[1].strip()
            elif re.match(r'<\d{4}-\d{2}-\d{2}.*>', line) or re.match(r'<\d{4}-\d{2}-\d{2}.*>--<\d{4}-\d{2}-\d{2}.*>', line):
                # This is the scheduling line (single or multi-day)
                current_event['scheduling'] = line
            else:
                current_content.append(line)
    
    # Save last event
    if current_event and current_event['id']:
        events[current_event['id']] = {
            'header': current_event['header'],
            'properties': current_event['properties'],
            'scheduling': current_event['scheduling'],
            'content': '\n'.join(current_content)
        }
    
    return events

def extract_agenda(content):
    """Extract agenda block from content"""
    agenda_pattern = re.compile(r'#\+begin_agenda\s*\n(.*?)\n#\+end_agenda', re.DOTALL | re.IGNORECASE)
    match = agenda_pattern.search(content)
    if match:
        return match.group(1).strip()
    return None

def update_agenda(content, new_agenda):
    """Update or add agenda block in content"""
    agenda_pattern = re.compile(r'#\+begin_agenda\s*\n.*?\n#\+end_agenda', re.DOTALL | re.IGNORECASE)
    
    # If there's an existing agenda block, replace it
    if agenda_pattern.search(content):
        updated_content = agenda_pattern.sub(f'#+begin_agenda\n{new_agenda}\n#+end_agenda', content)
        return updated_content
    
    # If there's no existing agenda, add one at the beginning
    return f'#+begin_agenda\n{new_agenda}\n#+end_agenda\n\n{content}'

def extract_description(properties):
    """Extract description from properties list"""
    for prop in properties:
        if prop.strip().startswith(':DESCRIPTION:'):
            return prop.split(':DESCRIPTION:')[1].strip()
    return None

def is_past_event(scheduling):
    """Check if an event is in the past"""
    if not scheduling:
        return False
    
    match = re.search(r'<(\d{4}-\d{2}-\d{2})', scheduling)
    if match:
        try:
            event_date = datetime.strptime(match.group(1), '%Y-%m-%d').date()
            return event_date < datetime.now().date()
        except ValueError:
            pass
    return False

def extract_title_content(header):
    """Extract the content from the header title (after * or * UPDATED: etc.)"""
    # Remove the * and any status prefixes
    title = re.sub(r'^\*\s+(CANCELED:\s+|CANCELLED:\s+|UPDATED:\s+)*', '', header)
    return title.strip()

def is_cancelled_header(header):
    """Check if a header already has CANCELLED or CANCELED prefix"""
    return bool(re.match(r'^\*\s+(CANCELED:|CANCELLED:)', header))

def add_cancelled_prefix(header):
    """Add CANCELLED prefix to header if it doesn't already have one"""
    if is_cancelled_header(header):
        return header
    return header.replace('* ', '* CANCELLED: ')

def merge_events(existing_events, new_events):
    """Merge existing and new events"""
    logger.debug("Merging events - existing: %d, new: %d", len(existing_events), len(new_events))
    merged_events = {}
    processed_ids = set()
    
    # Process all new events first (these are the current and future events)
    for event_id, event in new_events.items():
        processed_ids.add(event_id)
        
        if event_id in existing_events:
            # Event exists - update properties but keep user content
            existing_event = existing_events[event_id]
            
            # Don't update events that are in the past
            if is_past_event(existing_event['scheduling']):
                merged_events[event_id] = existing_event
                continue
            
            # Extract existing content without the agenda
            existing_content = existing_event['content']
            existing_agenda = extract_agenda(existing_content)
            
            # Get the new agenda from the content
            new_content = event['content'].strip()
            
            if new_content:
                # Use the content directly from the ics file as the agenda
                updated_content = update_agenda(existing_content, new_content)
            else:
                # Keep existing content as is
                updated_content = existing_content
            
            merged_events[event_id] = {
                'header': event['header'],  # Use new header (title might have changed)
                'properties': event['properties'],  # Use new properties (location might have changed)
                'scheduling': event['scheduling'],  # Use new scheduling (time might have changed)
                'content': updated_content  # Use updated content with new agenda but preserve notes
            }
        else:
            # New event - add everything and create agenda from content
            new_content = event['content'].strip()
            if new_content:
                # Create content with agenda block
                content = f'#+begin_agenda\n{new_content}\n#+end_agenda\n\n'
            else:
                # If no content, use title as fallback
                new_description = extract_title_content(event['header'])
                if new_description:
                    content = f'#+begin_agenda\n{new_description}\n#+end_agenda\n\n'
                else:
                    content = ''
                
            merged_events[event_id] = {
                'header': event['header'],
                'properties': event['properties'],
                'scheduling': event['scheduling'],
                'content': content
            }
    
    # Add events from existing file that weren't in new events (including canceled ones)
    for event_id, event in existing_events.items():
        if event_id not in processed_ids:
            # Don't modify past events
            if is_past_event(event['scheduling']):
                merged_events[event_id] = event
                continue
                
            # This event is no longer in the calendar - mark as canceled but keep it
            canceled_header = add_cancelled_prefix(event['header'])
            
            # Update status property to CANCELLED
            updated_properties = []
            for prop in event['properties']:
                if prop.strip().startswith(':STATUS:'):
                    updated_properties.append(':STATUS:        CANCELLED')
                else:
                    updated_properties.append(prop)
            
            merged_events[event_id] = {
                'header': canceled_header,
                'properties': updated_properties,
                'scheduling': event['scheduling'],
                'content': event['content']
            }
    
    return merged_events

def is_all_day_event(scheduling, properties) -> bool:
    """Check if an event is an all-day event"""
    logger.debug("Checking if event is all-day: %s", scheduling)
    if not scheduling:
        return False
        
    # Check if already in all-day format (no time information)
    try:
        pattern = r'<\d{4}-\d{2}-\d{2}\s+\w+>(?:--<\d{4}-\d{2}-\d{2}\s+\w+>)?$'
        result = re.search(pattern, scheduling)
        if result:
            logger.debug("Event is already in all-day format")
            return True
    except Exception as e:
        logger.error("Error in all-day format check: %s", e)
        logger.error("Scheduling value causing error: %r", scheduling)
    
    # Check for single day all-day event that starts and ends at 00:00
    try:
        single_day_match = re.search(r'<\d{4}-\d{2}-\d{2}.*\s00:00>--<\d{4}-\d{2}-\d{2}.*\s00:00>', scheduling)
        if single_day_match:
            logger.debug("Event is single day all-day event (00:00 to 00:00)")
            return True
    except Exception as e:
        logger.error("Error in single day check: %s", e)
        
    # Check for single time with 00:00 (e.g., start of all-day event)
    try:
        if re.search(r'<\d{4}-\d{2}-\d{2}.*\s00:00>', scheduling) and not re.search(r'--', scheduling):
            logger.debug("Event has single time 00:00, likely all-day")
            return True
    except Exception as e:
        logger.error("Error in single time check: %s", e)
        
    # Check for multi-day event that starts and ends at 00:00
    try:
        if re.search(r'<\d{4}-\d{2}-\d{2}.*\s00:00>--<\d{4}-\d{2}-\d{2}', scheduling):
            # Only if both times are 00:00 or there are no specific times
            if re.search(r'00:00>--.*00:00', scheduling) or not re.search(r'\d{2}:\d{2}', scheduling):
                logger.debug("Event is multi-day all-day event")
                return True
    except Exception as e:
        logger.error("Error in multi-day event check: %s", e)
    
    # Check for ALLDAY property (though according to tests this isn't reliable)
    for prop in properties:
        if prop.strip().startswith(':ALLDAY:') and 'true' in prop.lower():
            logger.debug("Event has ALLDAY property")
            return True
    
    logger.debug("Event is not all-day")
    return False

def format_scheduling(scheduling):
    """Format scheduling line, removing time for all-day events"""
    logger.debug("Formatting scheduling line: %s", scheduling)
    if not scheduling:
        return scheduling
    
    # Skip if it's already in the correct all-day format (no time information)
    try:
        pattern = r'<\d{4}-\d{2}-\d{2}\s+\w+>(?:--<\d{4}-\d{2}-\d{2}\s+\w+>)?$'
        if re.search(pattern, scheduling):
            logger.debug("Scheduling already in all-day format, returning as-is")
            return scheduling
    except Exception as e:
        logger.error("Error in regex pattern match: %s", e)
        logger.error("Scheduling value: %r", scheduling)
    
    # For multi-day all-day events, handle specially to match expected test output
    try:
        multi_day_match = re.search(r'<(\d{4}-\d{2}-\d{2})\s+(\w+)\s+00:00>--<(\d{4}-\d{2}-\d{2})\s+(\w+)(?:\s+00:00)?>', scheduling)
        if multi_day_match:
            start_date = multi_day_match.group(1)
            start_day = multi_day_match.group(2)
            end_date = multi_day_match.group(3)
            end_day = multi_day_match.group(4)
            
            try:
                # Parse start and end dates to calculate duration
                start_dt = datetime.strptime(f"{start_date}", '%Y-%m-%d')
                end_dt = datetime.strptime(f"{end_date}", '%Y-%m-%d')
                
                # Calculate the real duration (end date is exclusive in iCalendar format)
                duration = (end_dt - start_dt).days
                logger.debug("Multi-day event duration: %d days", duration)
                
                if duration == 1:
                    # If it's a one-day event (e.g., Sun 00:00 to Mon 00:00 is just Sunday)
                    result = f'<{start_date} {start_day}>'
                    logger.debug("Formatted as one-day event: %s", result)
                    return result
                else:
                    # For multi-day events, adjust the end date to be the last inclusive day
                    # Subtract 1 day from end date (exclusive to inclusive conversion)
                    adjusted_end_dt = end_dt - timedelta(days=1)
                    adjusted_end_date = adjusted_end_dt.strftime('%Y-%m-%d')
                    
                    # Get the correct day abbreviation
                    day_map = {
                        0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'
                    }
                    adjusted_end_day = day_map[adjusted_end_dt.weekday()]
                    
                    # Format for multi-day, with end date inclusive
                    result = f'<{start_date} {start_day}>--<{adjusted_end_date} {adjusted_end_day}>'
                    logger.debug("Formatted as multi-day event: %s", result)
                    return result
            except ValueError as e:
                # If date parsing fails, just return as is
                logger.error("Error parsing dates: %s", e)
                return scheduling
    except Exception as e:
        logger.error("Error in multi-day processing: %s", e)
    
    # For single-day all-day events, format as <YYYY-MM-DD DAY> without time
    try:
        single_day_match = re.search(r'<(\d{4}-\d{2}-\d{2})\s+(\w+)\s+00:00>', scheduling)
        if single_day_match:
            date_str = single_day_match.group(1)
            day_str = single_day_match.group(2)
            result = f'<{date_str} {day_str}>'
            logger.debug("Formatted as single all-day event: %s", result)
            return result
    except Exception as e:
        logger.error("Error in single-day processing: %s", e)
    
    # Return original scheduling for events that don't match all-day patterns
    logger.debug("No formatting applied, returning original")
    return scheduling

def events_to_org(events, format_dates=True):
    """Convert events dictionary back to org format
    
    Args:
        events: Dictionary of events to convert
        format_dates: Whether to format all-day and multi-day events (default: True)
    """
    logger.debug("Converting %d events to org format (format_dates=%s)", len(events), format_dates)
    org_content = []
    
    # Sort events by scheduled time
    def event_sort_key(event_tuple):
        event_id, event = event_tuple
        # Extract date and time from scheduling line
        if event['scheduling']:
            # First try to match regular events with time
            match = re.search(r'<(\d{4}-\d{2}-\d{2}\s+\w+\s+\d{2}:\d{2})', event['scheduling'])
            if match:
                try:
                    return datetime.strptime(match.group(1), '%Y-%m-%d %a %H:%M')
                except ValueError:
                    pass
            
            # Then try to match all-day events
            all_day_match = re.search(r'<(\d{4}-\d{2}-\d{2})', event['scheduling'])
            if all_day_match:
                try:
                    # Use noon as the time for all-day events for sorting purposes
                    date_str = all_day_match.group(1)
                    return datetime.strptime(f"{date_str} 12:00", '%Y-%m-%d %H:%M')
                except ValueError:
                    pass
        # Default to far future for events without valid scheduling
        return datetime(2099, 12, 31)
    
    sorted_events = sorted(events.items(), key=event_sort_key)
    
    for i, (event_id, event) in enumerate(sorted_events):
        # Check if this is an all-day event
        all_day = is_all_day_event(event['scheduling'], event['properties'])
        
        org_content.append(event['header'])
        org_content.append('\n'.join(event['properties']))
        
        # Format scheduling differently for all-day events if format_dates is True
        if event['scheduling']:
            if all_day and format_dates:
                formatted = format_scheduling(event['scheduling'])
                logger.debug("Event %s scheduling formatted from %r to %r", 
                            event_id[:8], event['scheduling'], formatted)
                org_content.append(formatted)
            else:
                org_content.append(event['scheduling'])
                
        if event['content'].strip():
            # Don't add extra newline if the content already has one at the end
            content_to_add = event['content'].rstrip()
            org_content.append(content_to_add)
        
        # Add exactly two blank lines between events (to create one blank line in the output)
        if i < len(sorted_events) - 1:
            # Make sure we're not adding more blank lines than needed
            while org_content and org_content[-1] == '':
                org_content.pop()
            
            org_content.append('')
            org_content.append('')
    
    # Remove trailing newlines at the end of the file
    return '\n'.join(org_content).rstrip()

def main():
    logger.info("Starting ics-to-org sync")
    parser = argparse.ArgumentParser(description='Sync org-mode file with icsorg calendar data')
    parser.add_argument('--ics-url', required=True, help='iCalendar URL')
    parser.add_argument('--org-file', required=True, help='Org file to update')
    parser.add_argument('--author', required=True, help='Author name')
    parser.add_argument('--email', required=True, help='Author email')
    parser.add_argument('--no-format-dates', action='store_true',
                     help='Disable the formatting of all-day and multi-day events (keep raw timestamps)')
    parser.add_argument('--debug', action='store_true',
                     help='Enable debug logging')
    args = parser.parse_args()
    
    # Set logging level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    else:
        logger.setLevel(logging.INFO)
    
    # Get temp file name for icsorg output
    with tempfile.NamedTemporaryFile(suffix='.org', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    try:
        # Run icsorg to get latest calendar data
        print(f"Fetching latest calendar data from {args.ics_url}...")
        run_icsorg(args.ics_url, temp_filename, args.author, args.email)
        
        # Check if our target org file exists
        if not os.path.exists(args.org_file):
            print(f"Output file {args.org_file} doesn't exist. Creating new file.")
            os.rename(temp_filename, args.org_file)
            print("Done!")
            return
        
        # Read both files
        with open(args.org_file, 'r') as f:
            existing_content = f.read()
        
        with open(temp_filename, 'r') as f:
            new_content = f.read()
        
        # Parse both files
        existing_events = parse_org_events(existing_content)
        new_events = parse_org_events(new_content)
        
        # Merge events
        merged_events = merge_events(existing_events, new_events)
        
        # Convert back to org format, respecting the date formatting option
        format_dates = not args.no_format_dates
        logger.debug("Using format_dates=%s", format_dates)
        merged_content = events_to_org(merged_events, format_dates=format_dates)
        
        # Log a sample of the output
        if args.debug:
            logger.debug("First 300 chars of merged content: %s", merged_content[:300])
            logger.debug("Last 300 chars of merged content: %s", merged_content[-300:] if len(merged_content) > 300 else merged_content)
            logger.debug("Merged content has %d lines", len(merged_content.splitlines()))
        
        # Write merged content
        with open(args.org_file, 'w') as f:
            f.write(merged_content)
        
        logger.info("Successfully merged calendar data with existing notes in %s!", args.org_file)
        print(f"Successfully merged calendar data with existing notes in {args.org_file}!")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    main()