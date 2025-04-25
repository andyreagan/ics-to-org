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
    
    # Convert back to org format (with date formatting on as it is by default)
    merged_content = events_to_org(merged_events, format_dates=True)
    
    # Normalize content for comparison (standardize blank lines)
    def normalize_content(content):
        # Replace multiple consecutive newlines with exactly two newlines
        lines = content.splitlines()
        normalized_lines = []
        for line in lines:
            if not line.strip() and normalized_lines and not normalized_lines[-1].strip():
                # Skip consecutive blank lines
                continue
            normalized_lines.append(line)
        return '\n'.join(normalized_lines)
    
    # Normalize both contents for consistent comparison
    normalized_merged = normalize_content(merged_content)
    normalized_expected = normalize_content(expected_content)
    
    # Check if merged content matches expected content
    if normalized_merged.strip() != normalized_expected.strip():
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
    assert normalized_merged.strip() == normalized_expected.strip(), "Contents should match"
