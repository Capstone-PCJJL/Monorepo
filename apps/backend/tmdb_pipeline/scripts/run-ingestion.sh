#!/bin/bash
# =============================================================================
# Run Initial Ingestion Script
# =============================================================================
# This script runs the initial ingestion with proper logging and notifications.
#
# Usage:
#   ./tmdb_pipeline/scripts/run-ingestion.sh              # Full ingestion
#   ./tmdb_pipeline/scripts/run-ingestion.sh --test 100   # Test with 100 movies
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_DIR"

# Parse arguments
TEST_LIMIT=""
if [ "$1" == "--test" ] && [ -n "$2" ]; then
    TEST_LIMIT="--test-limit $2"
    echo "Running in TEST MODE with limit: $2"
fi

# Create logs directory
mkdir -p tmdb_pipeline/logs

# Log file with timestamp
LOGFILE="tmdb_pipeline/logs/ingestion_$(date +%Y%m%d_%H%M%S).log"

echo "=========================================="
echo "TMDB Pipeline - Initial Ingestion"
echo "=========================================="
echo "Started at: $(date)"
echo "Log file: $LOGFILE"
echo "=========================================="

# Check connection first
echo "Testing connections..."
python3 -m tmdb_pipeline test

# Show current status
echo ""
echo "Current database status:"
python3 -m tmdb_pipeline status

# Confirm before proceeding (skip if in test mode)
if [ -z "$TEST_LIMIT" ]; then
    echo ""
    echo "WARNING: Full ingestion can take many hours!"
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

# Run ingestion
echo ""
echo "Starting ingestion..."
echo "=========================================="

# Run with output to both terminal and log file
python3 -m tmdb_pipeline initial $TEST_LIMIT 2>&1 | tee -a "$LOGFILE"

# Final status
echo ""
echo "=========================================="
echo "Ingestion Complete!"
echo "=========================================="
echo "Finished at: $(date)"
python3 -m tmdb_pipeline status
