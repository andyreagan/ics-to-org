from setuptools import setup
import os

# Read the contents of README.md, or use a simple description if not found
readme_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md")
try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Sync iCalendar events to org-mode files while preserving your notes."

setup(
    name="ics-to-org",
    version="0.3.0",
    author="Andy Reagan",
    author_email="andy@andyreagan.com",
    description="Sync iCalendar events to org-mode files while preserving your notes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/andyreagan/ics-to-org",
    py_modules=["sync_calendar"],
    package_dir={"": "src"},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Text Editors :: Emacs",
    ],
    entry_points={
        "console_scripts": [
            "sync_calendar=sync_calendar:main",
        ],
    },
    install_requires=[
        # No direct dependency on icsorg as it's not available on PyPI
        # It can be installed separately with: npm install -g icsorg
    ],
    extras_require={
        "dev": ["pytest", "pytest-cov"],
    },
    python_requires=">=3.10",
)
