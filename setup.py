from setuptools import setup

setup(
    name="ics-to-org",
    version="0.1.0",
    py_modules=["sync_calendar"],
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "sync_calendar=sync_calendar:main",
        ],
    },
    python_requires=">=3.6",
)