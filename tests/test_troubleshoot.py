import sys
import os
import logging

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.sync_calendar import parse_org_events, merge_events, events_to_org

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test-troubleshoot')

def load_file(filename):
    test_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(test_dir, filename)
    
    with open(file_path, 'r') as f:
        content = f.read()
        
    return content

import pytest

@pytest.mark.skip(reason="This is a troubleshooting test for understanding the problematic event")
def test_problematic_event():
    """Analyze the problematic event to understand the issue"""
    # Load test files
    existing_content = load_file("existing_org_file.org")
    new_content = load_file("updated_ics_org.org")
    expected_content = load_file("expected_output_org.org")
    
    # Parse files
    existing_events = parse_org_events(existing_content)
    new_events = parse_org_events(new_content)
    
    # The ID of the problematic event
    problematic_id = '040000008200E00074C5B7101A82E00800000000A0895B0C7DAFDB01000000000000000010000000046BD7A11BA62741B6CEA3CCB373B966'
    
    # Check if the event exists in both files
    assert problematic_id in existing_events, "Problematic event should exist in existing events"
    assert problematic_id in new_events, "Problematic event should exist in new events"
    
    # Log the event details from both files
    existing_event = existing_events[problematic_id]
    new_event = new_events[problematic_id]
    
    print("\nExisting event:")
    print(f"  Header: {existing_event['header']}")
    print(f"  Scheduling: {existing_event['scheduling']}")
    print(f"  Properties: {existing_event['properties']}")
    print(f"  Content: {existing_event['content']}")
    
    print("\nNew event:")
    print(f"  Header: {new_event['header']}")
    print(f"  Scheduling: {new_event['scheduling']}")
    print(f"  Properties: {new_event['properties']}")
    print(f"  Content: {new_event['content']}")
    
    # Merge to see what the result is
    merged_events = merge_events({problematic_id: existing_event}, {problematic_id: new_event})
    
    # Examine the merged event
    merged_event = merged_events[problematic_id]
    print("\nMerged event:")
    print(f"  Header: {merged_event['header']}")
    print(f"  Scheduling: {merged_event['scheduling']}")
    print(f"  Properties: {merged_event['properties']}")
    print(f"  Content: {merged_event['content']}")
    
    # In the expected output, what is this event supposed to look like?
    expected_events = parse_org_events(expected_content)
    expected_event = expected_events[problematic_id]
    
    print("\nExpected event:")
    print(f"  Header: {expected_event['header']}")
    print(f"  Scheduling: {expected_event['scheduling']}")
    print(f"  Properties: {expected_event['properties']}")
    print(f"  Content: {expected_event['content']}")
    
    # Compare the merged event with the expected event
    assert merged_event['header'] == expected_event['header'], "Headers should match"
    assert merged_event['scheduling'] == expected_event['scheduling'], "Scheduling should match"
    
    # Check for specific property differences
    for prop_name in [':DURATION:', ':STATUS:', ':LOCATION:']:
        merged_prop = next((p for p in merged_event['properties'] if prop_name in p), None)
        expected_prop = next((p for p in expected_event['properties'] if prop_name in p), None)
        print(f"\nProperty {prop_name}:")
        print(f"  Merged: {merged_prop}")
        print(f"  Expected: {expected_prop}")

    # Check content differences
    print("\nContent comparison:")
    print(f"  Merged content: {merged_event['content']}")
    print(f"  Expected content: {expected_event['content']}")

if __name__ == "__main__":
    test_problematic_event()