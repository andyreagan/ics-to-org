# test_sync.py
import os
import difflib
from sync_calendar import parse_org_events, merge_events, events_to_org

def load_file(filename):
    test_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(test_dir, filename)
    with open(file_path, 'r') as f:
        return f.read()

def test_sync():
    # Load test files
    existing_content = load_file("existing_org_file.org")
    new_content = load_file("updated_ics_org.org")
    expected_content = load_file("expected_output_org.org")
    
    # Parse both files
    existing_events = parse_org_events(existing_content)
    new_events = parse_org_events(new_content)
    
    # Merge events
    merged_events = merge_events(existing_events, new_events)
    
    # Convert back to org format
    merged_content = events_to_org(merged_events)
    
    # Check if merged content matches expected content
    if merged_content.strip() != expected_content.strip():
        # Show differences if they don't match
        diff = '\n'.join(difflib.unified_diff(
            expected_content.splitlines(),
            merged_content.splitlines(),
            fromfile='expected',
            tofile='actual',
            lineterm=''
        ))
        assert False, f"Merged content does not match expected output:\n{diff}"
    
    # If we get here, the test passes
    assert merged_content.strip() == expected_content.strip(), "Contents should match"
