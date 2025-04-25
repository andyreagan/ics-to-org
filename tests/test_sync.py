# test_sync.py
import os
import difflib
import logging
from sync_calendar import parse_org_events, merge_events, events_to_org

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test-sync')

def load_file(filename):
    test_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(test_dir, filename)
    logger.debug("Loading file: %s", file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
        
    # Log the first 200 characters of the file for debugging
    logger.debug("First 200 chars of %s: %r", filename, content[:200])
    return content

def test_sync():
    # Load test files
    logger.debug("Starting test_sync")
    existing_content = load_file("existing_org_file.org")
    new_content = load_file("updated_ics_org.org")
    expected_content = load_file("expected_output_org.org")
    
    logger.debug(f"Loaded test files - existing: {len(existing_content)} chars, new: {len(new_content)} chars, expected: {len(expected_content)} chars")
    
    # Parse both files
    existing_events = parse_org_events(existing_content)
    new_events = parse_org_events(new_content)
    
    # Merge events
    logger.debug("Existing events IDs: %s", list(existing_events.keys()))
    logger.debug("New events IDs: %s", list(new_events.keys()))
    
    # Check for the problematic event specifically
    problematic_id = '040000008200E00074C5B7101A82E00800000000A0895B0C7DAFDB01000000000000000010000000046BD7A11BA62741B6CEA3CCB373B966'
    if problematic_id in existing_events:
        logger.debug("Existing problematic event: %s", existing_events[problematic_id])
    if problematic_id in new_events:
        logger.debug("New problematic event: %s", new_events[problematic_id])
    
    merged_events = merge_events(existing_events, new_events)
    logger.debug("Merged events IDs: %s", list(merged_events.keys()))
    
    # Convert back to org format (with date formatting on as it is by default)
    merged_content = events_to_org(merged_events, format_dates=True)
    
    # Debug the output specifically to see differences
    logger.debug("First 200 chars of merged content: %s", merged_content[:200])
    
    # Normalize content for comparison (standardize blank lines and whitespace)
    def normalize_content(content):
        logger.debug("Normalizing content with length: %d", len(content))
        
        # Split by lines, normalize line endings
        lines = content.replace('\r\n', '\n').splitlines()
        logger.debug("After splitting, got %d lines", len(lines))
        normalized_lines = []
        
        # Process lines to standardize whitespace
        for i, line in enumerate(lines):
            # Skip consecutive blank lines
            if not line.strip() and normalized_lines and not normalized_lines[-1].strip():
                logger.debug("Skipping blank line at index %d", i)
                continue
                
            # Standardize whitespace within lines (trim trailing spaces, etc.)
            normalized_line = line.rstrip()
            normalized_lines.append(normalized_line)
            
        logger.debug("After normalization, got %d lines", len(normalized_lines))
        
        # Join with consistent line endings
        result = '\n'.join(normalized_lines)
        logger.debug("Normalized content length: %d", len(result))
        return result
    
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
        
        # Log the entire content for debugging
        logger.debug("Expected content (normalized):")
        for i, line in enumerate(norm_expected_lines):
            logger.debug("  %d: %s", i+1, line)
            
        logger.debug("Actual content (normalized):")
        for i, line in enumerate(norm_merged_lines):
            logger.debug("  %d: %s", i+1, line)
        
        for i in range(min(len(norm_expected_lines), len(norm_merged_lines))):
            if norm_expected_lines[i] != norm_merged_lines[i]:
                line_diffs.append(f"Line {i+1} differs:")
                line_diffs.append(f"  Expected: '{norm_expected_lines[i]}'")
                line_diffs.append(f"  Actual:   '{norm_merged_lines[i]}'")
                # Log details to diagnose the issue
                logger.debug("Difference at line %d:", i+1)
                logger.debug("  Expected: %r", norm_expected_lines[i])
                logger.debug("  Actual:   %r", norm_merged_lines[i])
        
        # Add message if line counts differ
        if len(norm_expected_lines) != len(norm_merged_lines):
            line_diffs.append(f"Line count differs: expected {len(norm_expected_lines)}, got {len(norm_merged_lines)}")
        
        line_diff_str = "\n".join(line_diffs)
        assert False, f"Merged content does not match expected output:\n{diff}\n\nLine-by-line differences:\n{line_diff_str}"
    
    # If we get here, the test passes
    assert normalized_merged.strip() == normalized_expected.strip(), "Contents should match"
