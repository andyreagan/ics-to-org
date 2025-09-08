#!/bin/bash
# Generate README.md from README.org when needed
# This is only for external tools that require .md format

if command -v pandoc &> /dev/null; then
    pandoc -f org -t gfm --wrap=none --standalone README.org -o README.md
    echo "Generated README.md from README.org"
else
    echo "Warning: pandoc not found. Install it with: brew install pandoc"
    exit 1
fi
