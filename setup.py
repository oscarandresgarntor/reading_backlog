"""Setup configuration for the reading backlog CLI."""

from setuptools import setup, find_packages

setup(
    name="reading-backlog",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.0",
        "typer>=0.9.0",
        "rich>=13.7.0",
        "httpx>=0.26.0",
        "trafilatura>=1.6.0",
        "lxml_html_clean>=0.4.0",
        "pymupdf>=1.23.0",
        "jinja2>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "reading=src.cli.commands:main",
        ],
    },
    python_requires=">=3.9",
    author="Your Name",
    description="A reading backlog system with CLI, API, and Chrome extension",
)
