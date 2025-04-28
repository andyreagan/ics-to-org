from sync_calendar import extract_agenda, update_agenda


def test_extract_agenda():
    """Test extracting agenda from content"""
    # Content with agenda block
    content_with_agenda = """Some text before.

#+begin_agenda
This is the agenda content.
It has multiple lines.
#+end_agenda

Some text after.
"""

    # Test successful extraction
    result = extract_agenda(content_with_agenda)
    assert result == "This is the agenda content.\nIt has multiple lines."

    # Content with no agenda block
    content_without_agenda = "This content has no agenda block."
    result = extract_agenda(content_without_agenda)
    assert result is None

    # Content with empty agenda block
    content_with_empty_agenda = """
#+begin_agenda
#+end_agenda
"""
    result = extract_agenda(content_with_empty_agenda)
    assert result == ""


def test_update_agenda_existing():
    """Test updating an existing agenda block"""
    content = """Some text before.

#+begin_agenda
Old agenda content.
#+end_agenda

Some text after.
"""

    new_agenda = "New agenda content."

    result = update_agenda(content, new_agenda)

    assert "Old agenda content." not in result
    assert "New agenda content." in result
    assert "Some text before." in result
    assert "Some text after." in result
    assert result.count("#+begin_agenda") == 1
    assert result.count("#+end_agenda") == 1


def test_update_agenda_no_existing():
    """Test adding an agenda block when none exists"""
    content = "Content without any agenda block."

    new_agenda = "New agenda content."

    result = update_agenda(content, new_agenda)

    assert "#+begin_agenda" in result
    assert "New agenda content." in result
    assert "#+end_agenda" in result
    assert "Content without any agenda block." in result

    # The new agenda should be at the beginning
    lines = result.split("\n")
    assert "#+begin_agenda" in lines[0]


def test_update_agenda_case_insensitive():
    """Test that agenda extraction and update are case-insensitive"""
    content = """Some text.

#+BEGIN_AGENDA
Mixed case agenda.
#+END_AGENDA

More text.
"""

    # Extract should work with any case
    result = extract_agenda(content)
    assert result == "Mixed case agenda."

    # Update should work with any case
    new_agenda = "New content."
    result = update_agenda(content, new_agenda)
    assert "New content." in result
    assert "Mixed case agenda." not in result
