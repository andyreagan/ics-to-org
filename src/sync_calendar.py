#!/usr/bin/env python3
import subprocess
import re
import os
import tempfile
from datetime import datetime
import argparse

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
            elif re.match(r'<\d{4}-\d{2}-\d{2}.*>', line):
                # This is the scheduling line
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

def merge_events(existing_events, new_events):
    """Merge existing and new events"""
    merged_events = {}
    processed_ids = set()
    
    # Process all new events first (these are the current and future events)
    for event_id, event in new_events.items():
        processed_ids.add(event_id)
        
        if event_id in existing_events:
            # Event exists - update properties but keep user content
            existing_event = existing_events[event_id]
            
            # Extract existing content without the agenda
            existing_content = existing_event['content']
            existing_agenda = extract_agenda(existing_content)
            
            # Get the new agenda from the description field if available
            new_description = extract_description(event['properties'])
            
            if new_description and (not existing_agenda or existing_agenda != new_description):
                # Update the agenda in the existing content
                updated_content = update_agenda(existing_content, new_description)
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
            # New event - add everything and create agenda from description if available
            new_description = extract_description(event['properties'])
            if new_description:
                # Create content with agenda block
                content = f'#+begin_agenda\n{new_description}\n#+end_agenda\n\n'
            else:
                content = ''
                
            merged_events[event_id] = {
                'header': event['header'],
                'properties': event['properties'],
                'scheduling': event['scheduling'],
                'content': content
            }
    
    # Add canceled events from existing file (events not in new file)
    for event_id, event in existing_events.items():
        if event_id not in processed_ids:
            # This event is no longer in the calendar - mark as canceled but keep it
            canceled_header = event['header']
            if not canceled_header.startswith('* CANCELED:'):
                canceled_header = canceled_header.replace('* ', '* CANCELED: ')
            
            merged_events[event_id] = {
                'header': canceled_header,
                'properties': event['properties'],
                'scheduling': event['scheduling'],
                'content': event['content']
            }
    
    return merged_events

def events_to_org(events):
    """Convert events dictionary back to org format"""
    org_content = []
    
    # Sort events by scheduled time
    def event_sort_key(event_tuple):
        event_id, event = event_tuple
        # Extract date and time from scheduling line
        if event['scheduling']:
            match = re.search(r'<(\d{4}-\d{2}-\d{2}\s+\w+\s+\d{2}:\d{2})', event['scheduling'])
            if match:
                try:
                    return datetime.strptime(match.group(1), '%Y-%m-%d %a %H:%M')
                except ValueError:
                    pass
        # Default to far future for events without valid scheduling
        return datetime(2099, 12, 31)
    
    sorted_events = sorted(events.items(), key=event_sort_key)
    
    for event_id, event in sorted_events:
        org_content.append(event['header'])
        org_content.append('\n'.join(event['properties']))
        if event['scheduling']:
            org_content.append(event['scheduling'])
        if event['content'].strip():
            org_content.append(event['content'])
        org_content.append('')  # Empty line between events
    
    return '\n'.join(org_content)

def main():
    parser = argparse.ArgumentParser(description='Sync org-mode file with icsorg calendar data')
    parser.add_argument('--ics-url', required=True, help='iCalendar URL')
    parser.add_argument('--org-file', required=True, help='Org file to update')
    parser.add_argument('--author', required=True, help='Author name')
    parser.add_argument('--email', required=True, help='Author email')
    args = parser.parse_args()
    
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
        
        # Convert back to org format
        merged_content = events_to_org(merged_events)
        
        # Write merged content
        with open(args.org_file, 'w') as f:
            f.write(merged_content)
        
        print(f"Successfully merged calendar data with existing notes in {args.org_file}!")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    main()