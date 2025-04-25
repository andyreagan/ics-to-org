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
    
    # Normalize content for comparison (standardize blank lines and whitespace)
    def normalize_content(content):
        # Split by lines, normalize line endings
        lines = content.replace('\r\n', '\n').splitlines()
        normalized_lines = []
        
        # Process lines to standardize whitespace
        for line in lines:
            # Skip consecutive blank lines
            if not line.strip() and normalized_lines and not normalized_lines[-1].strip():
                continue
                
            # Standardize whitespace within lines (trim trailing spaces, etc.)
            normalized_line = line.rstrip()
            normalized_lines.append(normalized_line)
            
        # Join with consistent line endings
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
        
        # Also provide line-by-line differences for easier debugging
        norm_expected_lines = normalized_expected.strip().splitlines()
        norm_merged_lines = normalized_merged.strip().splitlines()
        line_diffs = []
        
        for i in range(min(len(norm_expected_lines), len(norm_merged_lines))):
            if norm_expected_lines[i] != norm_merged_lines[i]:
                line_diffs.append(f"Line {i+1} differs:")
                line_diffs.append(f"  Expected: '{norm_expected_lines[i]}'")
                line_diffs.append(f"  Actual:   '{norm_merged_lines[i]}'")
        
        # Add message if line counts differ
        if len(norm_expected_lines) != len(norm_merged_lines):
            line_diffs.append(f"Line count differs: expected {len(norm_expected_lines)}, got {len(norm_merged_lines)}")
        
        line_diff_str = "\n".join(line_diffs)
        assert False, f"Merged content does not match expected output:\n{diff}\n\nLine-by-line differences:\n{line_diff_str}"
    
    # If we get here, the test passes
    assert normalized_merged.strip() == normalized_expected.strip(), "Contents should match"
