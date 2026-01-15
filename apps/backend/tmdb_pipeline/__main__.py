"""
Entry point for running the pipeline as a module.

Usage:
    python -m tmdb_pipeline <command>
"""

from .cli import main

if __name__ == "__main__":
    main()
