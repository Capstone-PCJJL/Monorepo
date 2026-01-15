"""
Command-line interface for TMDB Pipeline.

Provides commands for:
- setup: Check and create required tables
- status: Show current database status
- initial: Initial ingestion of movies
- add-new: Add new movies to pending
- update: Differential update of existing movies
- search: Search and add movies manually
- approve: Interactive approval workflow
- list-pending: List movies in pending queue
"""

import argparse
import sys
from typing import Optional

from .approval import ApprovalManager
from .client import TMDBClient
from .config import Config
from .database import DatabaseManager
from .pipeline import TMDBPipeline
from .utils import print_header, print_status_table, format_number


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands."""
    parser = argparse.ArgumentParser(
        prog="tmdb_pipeline",
        description="TMDB Movie Pipeline - Ingest, update, and manage movie data from TMDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup (run first)
  python -m tmdb_pipeline setup

  # Check status
  python -m tmdb_pipeline status

  # Test initial ingestion with 5 movies
  python -m tmdb_pipeline initial --test-limit 5

  # Add new movies
  python -m tmdb_pipeline add-new --test-limit 5

  # Search for a movie
  python -m tmdb_pipeline search "Inception"

  # Interactive approval
  python -m tmdb_pipeline approve

  # Quick approve all
  python -m tmdb_pipeline approve --quick
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Check for missing tables and create them",
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show current database status",
    )

    # Initial ingestion command
    initial_parser = subparsers.add_parser(
        "initial",
        help="Initial ingestion of movies from TMDB (for empty database)",
    )
    initial_parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of movies to process (for testing)",
    )
    initial_parser.add_argument(
        "--force",
        action="store_true",
        help="Force ingestion even if database has data (DANGEROUS)",
    )
    initial_parser.add_argument(
        "--start-year",
        type=int,
        help="Year to start from (default: current year)",
    )
    initial_parser.add_argument(
        "--end-year",
        type=int,
        help="Year to end at (default: earliest in TMDB)",
    )

    # Add new movies command
    add_new_parser = subparsers.add_parser(
        "add-new",
        help="Add new movies released after our latest movie",
    )
    add_new_parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of movies to add (for testing)",
    )

    # Differential update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update movies that have changed in TMDB",
    )
    update_parser.add_argument(
        "--days-back",
        type=int,
        default=14,
        help="Days back to check for changes (max 14, default: 14)",
    )
    update_parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of movies to update (for testing)",
    )

    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search TMDB for movies and add to pending",
    )
    search_parser.add_argument(
        "query",
        help="Movie title to search for, or TMDB ID",
    )
    search_parser.add_argument(
        "--add",
        type=int,
        metavar="ID",
        help="Directly add movie by TMDB ID",
    )

    # Approve command
    approve_parser = subparsers.add_parser(
        "approve",
        help="Interactive approval of pending movies",
    )
    approve_parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of movies to review",
    )
    approve_parser.add_argument(
        "--search",
        type=str,
        metavar="QUERY",
        help="Search pending movies and approve",
    )
    approve_parser.add_argument(
        "--movie-id",
        type=int,
        help="Approve specific movie by ID",
    )
    approve_parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick approve all without prompts (requires confirmation)",
    )

    # List pending command
    list_parser = subparsers.add_parser(
        "list-pending",
        help="List movies in pending queue",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of movies to show (default: 20)",
    )

    # Test connection command
    test_parser = subparsers.add_parser(
        "test",
        help="Test API and database connections",
    )

    # Drop/reset command
    drop_parser = subparsers.add_parser(
        "drop",
        help="Drop movie data tables (DANGEROUS - deletes all data)",
    )
    drop_parser.add_argument(
        "--pending-only",
        action="store_true",
        help="Only drop pending tables, keep production",
    )
    drop_parser.add_argument(
        "--production-only",
        action="store_true",
        help="Only drop production tables, keep pending",
    )
    drop_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # ============ NEW COMMANDS FOR COMPLETE INGESTION ============

    # Bulk ingest from export command
    bulk_parser = subparsers.add_parser(
        "bulk-ingest",
        help="Bulk ingest ALL movies from TMDB daily export (most comprehensive)",
    )
    bulk_parser.add_argument(
        "--min-popularity",
        type=float,
        default=0.0,
        help="Minimum popularity threshold (default: 0.0 = all movies)",
    )
    bulk_parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of movies to process (for testing)",
    )
    bulk_parser.add_argument(
        "--to-production",
        action="store_true",
        help="Insert directly to production tables (default: pending)",
    )
    bulk_parser.add_argument(
        "--slow-mode",
        action="store_true",
        help="Enable slow mode (20 req/sec) for safer batch operations",
    )

    # Verify command
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify database completeness against TMDB export",
    )
    verify_parser.add_argument(
        "--by-popularity",
        action="store_true",
        help="Show coverage breakdown by popularity tier",
    )

    # Backfill command
    backfill_parser = subparsers.add_parser(
        "backfill",
        help="Backfill missing movies identified by verification",
    )
    backfill_parser.add_argument(
        "--min-popularity",
        type=float,
        default=0.0,
        help="Minimum popularity threshold (default: 0.0 = all movies)",
    )
    backfill_parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of movies to process (for testing)",
    )
    backfill_parser.add_argument(
        "--to-production",
        action="store_true",
        help="Insert directly to production tables (default: pending)",
    )
    backfill_parser.add_argument(
        "--slow-mode",
        action="store_true",
        help="Enable slow mode (20 req/sec) for large batch operations",
    )

    # Reingest year command
    reingest_parser = subparsers.add_parser(
        "reingest-year",
        help="Re-ingest a specific year using monthly queries (captures all movies)",
    )
    reingest_parser.add_argument(
        "year",
        type=int,
        help="Year to re-ingest",
    )
    reingest_parser.add_argument(
        "--test-limit",
        type=int,
        help="Limit number of movies to process (for testing)",
    )
    reingest_parser.add_argument(
        "--to-production",
        action="store_true",
        help="Insert directly to production tables (default: pending)",
    )
    reingest_parser.add_argument(
        "--slow-mode",
        action="store_true",
        help="Enable slow mode (20 req/sec) for safer batch operations",
    )

    return parser


def cmd_setup(pipeline: TMDBPipeline) -> int:
    """Run setup command."""
    print_header("TMDB Pipeline Setup")

    result = pipeline.setup_database()

    print("\nProduction tables:")
    for table in DatabaseManager.PRODUCTION_TABLES:
        if table in result["existing_production"]:
            print(f"  {table:<20} EXISTS")
        elif table in result["created_production"]:
            print(f"  {table:<20} CREATED")
        else:
            print(f"  {table:<20} MISSING")

    print("\nPending tables:")
    for table in DatabaseManager.PENDING_TABLES:
        if table in result["existing_pending"]:
            print(f"  {table:<20} EXISTS")
        elif table in result["created_pending"]:
            print(f"  {table:<20} CREATED")
        else:
            print(f"  {table:<20} MISSING")

    created_count = len(result["created_production"]) + len(result["created_pending"])
    existing_count = len(result["existing_production"]) + len(result["existing_pending"])

    print(f"\nSetup complete! {created_count} tables created, {existing_count} already existed.")

    if result["all_present"]:
        print("All required tables are now present.")
        return 0
    else:
        print("WARNING: Some tables are still missing!")
        return 1


def cmd_status(pipeline: TMDBPipeline) -> int:
    """Run status command."""
    print_header("TMDB Pipeline Status")

    status = pipeline.get_status()

    print_status_table(
        {
            "Production movies": format_number(status["production_count"]),
            "Pending movies": format_number(status["pending_count"]),
            "Latest production date": status["latest_production_date"] or "N/A",
            "Latest pending date": status["latest_pending_date"] or "N/A",
            "All tables exist": "Yes" if status["all_tables_exist"] else "No",
        },
        title="Database Status",
    )

    if status["missing_production_tables"]:
        print(f"Missing production tables: {', '.join(status['missing_production_tables'])}")
    if status["missing_pending_tables"]:
        print(f"Missing pending tables: {', '.join(status['missing_pending_tables'])}")

    if not status["all_tables_exist"]:
        print("\nRun 'python -m tmdb_pipeline setup' to create missing tables.")

    return 0


def cmd_initial(pipeline: TMDBPipeline, args) -> int:
    """Run initial ingestion command."""
    print_header("Initial Ingestion")

    if args.test_limit:
        print(f"TEST MODE: Limited to {args.test_limit} movies\n")

    try:
        result = pipeline.initial_ingest(
            test_limit=args.test_limit,
            force=args.force,
            start_year=args.start_year,
            end_year=args.end_year,
        )
        print_status_table(result, title="Results")
        return 0

    except RuntimeError as e:
        print(f"\nERROR: {e}")
        return 1


def cmd_add_new(pipeline: TMDBPipeline, args) -> int:
    """Run add new movies command."""
    print_header("Add New Movies")

    if args.test_limit:
        print(f"TEST MODE: Limited to {args.test_limit} movies\n")

    result = pipeline.add_new_movies(test_limit=args.test_limit)
    print_status_table(result, title="Results")
    return 0


def cmd_update(pipeline: TMDBPipeline, args) -> int:
    """Run differential update command."""
    print_header("Differential Update")

    if args.test_limit:
        print(f"TEST MODE: Limited to {args.test_limit} movies\n")

    result = pipeline.differential_update(
        days_back=args.days_back,
        test_limit=args.test_limit,
    )
    print_status_table(result, title="Results")
    return 0


def cmd_search(pipeline: TMDBPipeline, args) -> int:
    """Run search command."""
    print_header("Search Movies")

    # If --add flag is used, directly add by ID
    if args.add:
        result = pipeline.add_movie_by_id(args.add)
        if result["success"]:
            print(f"\nSuccess: {result['message']}")
            return 0
        else:
            print(f"\nFailed: {result['message']}")
            return 1

    # Search for movies
    results = pipeline.search_movies(args.query)

    if not results:
        print(f"\nNo movies found for '{args.query}'")
        return 0

    print(f"\nFound {len(results)} movies:\n")
    for i, movie in enumerate(results, 1):
        print(movie.display_line(i))

    print("  [0] Cancel")
    print()

    # Let user select a movie to add
    while True:
        try:
            selection = input("Select movie to add to pending (number): ").strip()
            if selection == "0" or selection == "":
                print("Cancelled.")
                return 0

            idx = int(selection) - 1
            if 0 <= idx < len(results):
                break
            print(f"Please enter a number between 1 and {len(results)}")
        except ValueError:
            print("Please enter a valid number")
        except EOFError:
            print("\nCancelled.")
            return 0

    selected = results[idx]

    # Check if already exists
    if selected.exists_in_production:
        print(f"\n'{selected.title}' already exists in production database")
        return 0
    if selected.exists_in_pending:
        print(f"\n'{selected.title}' already exists in pending queue")
        return 0

    # Add to pending
    result = pipeline.add_movie_by_id(selected.id)
    if result["success"]:
        print(f"\nSuccess: {result['message']}")
        return 0
    else:
        print(f"\nFailed: {result['message']}")
        return 1


def cmd_approve(db: DatabaseManager, config: Config, args) -> int:
    """Run approve command."""
    print_header("Approve Pending Movies")

    approval = ApprovalManager(db, config.log_dir)

    if args.quick:
        stats = approval.approve_all_quick()
    elif args.search:
        stats = approval.approve_by_search(args.search)
    elif args.movie_id:
        stats = approval.approve_by_id(args.movie_id)
    else:
        stats = approval.approve_interactive(limit=args.limit)

    # Print summary
    if stats.reviewed > 0:
        print(f"\nSummary: {stats.approved} approved, {stats.skipped} skipped, {stats.deleted} deleted")
        if stats.remaining_pending > 0:
            print(f"Remaining in pending: {format_number(stats.remaining_pending)}")

    return 0


def cmd_list_pending(db: DatabaseManager, config: Config, args) -> int:
    """Run list pending command."""
    approval = ApprovalManager(db, config.log_dir)
    approval.display_pending_list(limit=args.limit)
    return 0


def cmd_test(pipeline: TMDBPipeline) -> int:
    """Run test connection command."""
    print_header("Connection Test")

    result = pipeline.test_connection()

    print(f"\nAPI Connection: {'OK' if result['api_connected'] else 'FAILED'}")
    if result["api_error"]:
        print(f"  Error: {result['api_error']}")

    print(f"DB Connection: {'OK' if result['db_connected'] else 'FAILED'}")
    if result["db_error"]:
        print(f"  Error: {result['db_error']}")

    return 0 if result["api_connected"] and result["db_connected"] else 1


def cmd_drop(db: DatabaseManager, args) -> int:
    """Run drop tables command."""
    print_header("Drop Tables")

    # Determine which tables to drop
    drop_production = not args.pending_only
    drop_pending = not args.production_only

    # Show what will be dropped
    tables_to_drop = []
    if drop_production:
        tables_to_drop.extend(DatabaseManager.PRODUCTION_TABLES)
    if drop_pending:
        tables_to_drop.extend(DatabaseManager.PENDING_TABLES)

    if not tables_to_drop:
        print("No tables selected to drop.")
        return 0

    print("\nThe following tables will be DROPPED (all data deleted):")
    for table in tables_to_drop:
        print(f"  - {table}")

    # Get current counts
    if drop_production:
        prod_count = db.get_production_count()
        print(f"\nProduction movies to delete: {format_number(prod_count)}")
    if drop_pending:
        pending_count = db.get_pending_count()
        print(f"Pending movies to delete: {format_number(pending_count)}")

    # Confirm
    if not args.yes:
        print("\nThis action CANNOT be undone!")
        try:
            confirm = input("Type 'DROP' to confirm: ").strip()
            if confirm != "DROP":
                print("Cancelled.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0

    # Drop tables
    result = db.drop_tables(
        drop_production=drop_production,
        drop_pending=drop_pending
    )

    print(f"\nDropped {len(result['dropped'])} tables:")
    for table in result["dropped"]:
        print(f"  - {table}")

    if result["errors"]:
        print(f"\nErrors:")
        for error in result["errors"]:
            print(f"  - {error}")
        return 1

    print("\nDone. Run 'setup' to recreate tables.")
    return 0


# ============ NEW COMMAND HANDLERS ============


def cmd_bulk_ingest(pipeline: TMDBPipeline, args) -> int:
    """Run bulk ingest from export command."""
    print_header("Bulk Ingest from TMDB Export")

    if args.slow_mode:
        pipeline.client.enable_slow_mode()
        print("Slow mode enabled (20 requests/second)\n")

    if args.test_limit:
        print(f"TEST MODE: Limited to {args.test_limit} movies\n")

    target = "production" if args.to_production else "pending"
    print(f"Target: {target} tables")
    if args.min_popularity > 0:
        print(f"Minimum popularity: {args.min_popularity}")
    print()

    result = pipeline.bulk_ingest_from_export(
        min_popularity=args.min_popularity,
        test_limit=args.test_limit,
        to_pending=not args.to_production,
    )

    print_status_table(result, title="Results")
    return 0


def cmd_verify(pipeline: TMDBPipeline, args) -> int:
    """Run verification command."""
    print_header("Database Verification")

    if args.by_popularity:
        print("Analyzing coverage by popularity tier...\n")
        coverage = pipeline.get_coverage_by_popularity()

        for tier, stats in coverage.items():
            print(f"\n{tier}:")
            print(f"  Total in TMDB:  {stats['total']:>10,}")
            print(f"  In database:    {stats['in_database']:>10,}")
            print(f"  Missing:        {stats['missing']:>10,}")
            print(f"  Coverage:       {stats['coverage_percent']:>9.1f}%")
    else:
        print("Verifying against TMDB export...\n")
        result = pipeline.verify_database()
        print(result.summary())

        if result.missing_count > 0:
            print(f"\nTop 10 missing movie IDs: {result.missing_ids[:10]}")
            print("\nRun 'backfill' command to fetch missing movies.")

    return 0


def cmd_backfill(pipeline: TMDBPipeline, args) -> int:
    """Run backfill command."""
    print_header("Backfill Missing Movies")

    if args.slow_mode:
        pipeline.client.enable_slow_mode()
        print("Slow mode enabled (20 requests/second)\n")

    if args.test_limit:
        print(f"TEST MODE: Limited to {args.test_limit} movies\n")

    target = "production" if args.to_production else "pending"
    print(f"Target: {target} tables")
    if args.min_popularity > 0:
        print(f"Minimum popularity: {args.min_popularity}")
    print()

    result = pipeline.backfill_missing(
        min_popularity=args.min_popularity,
        test_limit=args.test_limit,
        to_pending=not args.to_production,
    )

    print_status_table(result, title="Results")
    return 0


def cmd_reingest_year(pipeline: TMDBPipeline, args) -> int:
    """Run reingest year command."""
    print_header(f"Re-ingest Year {args.year}")

    if args.slow_mode:
        pipeline.client.enable_slow_mode()
        print("Slow mode enabled (20 requests/second)\n")

    if args.test_limit:
        print(f"TEST MODE: Limited to {args.test_limit} movies\n")

    target = "production" if args.to_production else "pending"
    print(f"Target: {target} tables\n")

    result = pipeline.reingest_year_monthly(
        year=args.year,
        test_limit=args.test_limit,
        to_pending=not args.to_production,
    )

    print_status_table(result, title="Results")
    return 0


def main(args: Optional[list] = None) -> int:
    """Main entry point for CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    # Load configuration
    try:
        config = Config.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nMake sure your .env file contains:")
        print("  API_KEY=<your_tmdb_api_key>")
        print("  TMDB_BEARER_TOKEN=<your_bearer_token>")
        print("  DB_MODE=local (or remote)")
        print("  LOCAL_SQL_HOST, LOCAL_SQL_USER, LOCAL_SQL_PASS, LOCAL_SQL_DB")
        print("  (or REMOTE_SQL_* for DB_MODE=remote)")
        return 1

    # Create components
    try:
        db = DatabaseManager(config)
        client = TMDBClient(config)
        pipeline = TMDBPipeline(client, db, config)
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        return 1

    # Route to command handler
    try:
        if parsed_args.command == "setup":
            return cmd_setup(pipeline)
        elif parsed_args.command == "status":
            return cmd_status(pipeline)
        elif parsed_args.command == "initial":
            return cmd_initial(pipeline, parsed_args)
        elif parsed_args.command == "add-new":
            return cmd_add_new(pipeline, parsed_args)
        elif parsed_args.command == "update":
            return cmd_update(pipeline, parsed_args)
        elif parsed_args.command == "search":
            return cmd_search(pipeline, parsed_args)
        elif parsed_args.command == "approve":
            return cmd_approve(db, config, parsed_args)
        elif parsed_args.command == "list-pending":
            return cmd_list_pending(db, config, parsed_args)
        elif parsed_args.command == "test":
            return cmd_test(pipeline)
        elif parsed_args.command == "drop":
            return cmd_drop(db, parsed_args)
        # New commands for complete ingestion
        elif parsed_args.command == "bulk-ingest":
            return cmd_bulk_ingest(pipeline, parsed_args)
        elif parsed_args.command == "verify":
            return cmd_verify(pipeline, parsed_args)
        elif parsed_args.command == "backfill":
            return cmd_backfill(pipeline, parsed_args)
        elif parsed_args.command == "reingest-year":
            return cmd_reingest_year(pipeline, parsed_args)
        else:
            parser.print_help()
            return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
