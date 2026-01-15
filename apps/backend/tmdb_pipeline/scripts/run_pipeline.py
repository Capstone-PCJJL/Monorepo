#!/usr/bin/env python3
"""
Entry point script for TMDB Pipeline.

This script can be used to run the pipeline from the command line
or as an AWS Lambda handler.

Usage:
    # From command line
    python tmdb_pipeline/scripts/run_pipeline.py setup
    python tmdb_pipeline/scripts/run_pipeline.py status
    python tmdb_pipeline/scripts/run_pipeline.py initial --test-limit 5
    python tmdb_pipeline/scripts/run_pipeline.py add-new
    python tmdb_pipeline/scripts/run_pipeline.py approve

    # As Lambda handler
    The lambda_handler function can be used directly.
"""

import os
import sys

# Add project root to path (go up two levels: tmdb_pipeline/scripts -> tmdb_pipeline -> project_root)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tmdb_pipeline.cli import main
from tmdb_pipeline.config import Config
from tmdb_pipeline.client import TMDBClient
from tmdb_pipeline.database import DatabaseManager
from tmdb_pipeline.pipeline import TMDBPipeline


def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda handler for pipeline operations.

    Event structure:
    {
        "command": "add-new" | "update" | "initial" | "status",
        "test_limit": Optional[int],
        "days_back": Optional[int],  # For update command
        "force": Optional[bool],      # For initial command
    }

    Returns:
        Result dictionary with operation stats
    """
    command = event.get("command", "status")
    test_limit = event.get("test_limit")
    days_back = event.get("days_back", 14)
    force = event.get("force", False)

    # Initialize components
    config = Config.from_env()
    db = DatabaseManager(config)
    client = TMDBClient(config)
    pipeline = TMDBPipeline(client, db, config)

    # Execute command
    if command == "status":
        return {"statusCode": 200, "body": pipeline.get_status()}

    elif command == "initial":
        result = pipeline.initial_ingest(test_limit=test_limit, force=force)
        return {"statusCode": 200, "body": result}

    elif command == "add-new":
        result = pipeline.add_new_movies(test_limit=test_limit)
        return {"statusCode": 200, "body": result}

    elif command == "update":
        result = pipeline.differential_update(days_back=days_back, test_limit=test_limit)
        return {"statusCode": 200, "body": result}

    elif command == "setup":
        result = pipeline.setup_database()
        return {"statusCode": 200, "body": result}

    else:
        return {
            "statusCode": 400,
            "body": {"error": f"Unknown command: {command}"},
        }


if __name__ == "__main__":
    sys.exit(main())
