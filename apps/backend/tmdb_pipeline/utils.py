"""
Utility functions for TMDB Pipeline.

Provides logging setup, progress bars, rate limiting, and display helpers.
"""

import logging
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Optional, Iterator, TypeVar, Iterable

from tqdm import tqdm

T = TypeVar("T")


def setup_logger(
    name: str,
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    console_output: bool = True,
) -> logging.Logger:
    """
    Set up a logger with file and optional console handlers.

    Args:
        name: Logger name (used for both logger and log file)
        log_dir: Directory for log files (defaults to ./logs)
        level: Logging level
        console_output: Whether to also log to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    if log_dir is None:
        log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)  # Only warnings and above to console
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


class RateLimiter:
    """
    Token bucket rate limiter for API requests.

    Ensures we don't exceed a specified number of requests per second.
    Thread-safe implementation.
    """

    def __init__(self, requests_per_second: int = 40):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests allowed per second
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.timestamps: deque = deque(maxlen=requests_per_second)
        self.lock = Lock()

    def acquire(self) -> None:
        """
        Acquire permission to make a request.
        Blocks if rate limit would be exceeded.
        """
        with self.lock:
            now = time.time()

            # Clean old timestamps
            while self.timestamps and now - self.timestamps[0] > 1.0:
                self.timestamps.popleft()

            # If at capacity, wait
            if len(self.timestamps) >= self.requests_per_second:
                sleep_time = 1.0 - (now - self.timestamps[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time()
                    # Clean again after sleeping
                    while self.timestamps and now - self.timestamps[0] > 1.0:
                        self.timestamps.popleft()

            self.timestamps.append(now)

    def __enter__(self) -> "RateLimiter":
        self.acquire()
        return self

    def __exit__(self, *args) -> None:
        pass


def progress_bar(
    iterable: Iterable[T],
    total: Optional[int] = None,
    desc: str = "Processing",
    unit: str = "items",
    disable: bool = False,
) -> Iterator[T]:
    """
    Wrap an iterable with a progress bar.

    Args:
        iterable: Items to iterate over
        total: Total number of items (if known)
        desc: Description to show
        unit: Unit name for items
        disable: If True, disable progress bar output

    Yields:
        Items from the iterable
    """
    return tqdm(
        iterable,
        total=total,
        desc=desc,
        unit=unit,
        disable=disable,
        ncols=100,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )


def format_number(n: int) -> str:
    """Format number with commas for readability."""
    return f"{n:,}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def truncate_string(s: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to max length, adding suffix if truncated."""
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix


def print_header(text: str, char: str = "=", width: int = 60) -> None:
    """Print a header with decorative lines."""
    print(char * width)
    print(text.center(width))
    print(char * width)


def print_section(text: str, char: str = "-", width: int = 60) -> None:
    """Print a section divider with text."""
    print(f"\n{char * width}")
    print(text)
    print(char * width)


def print_key_value(key: str, value: str, key_width: int = 20) -> None:
    """Print a key-value pair with aligned formatting."""
    print(f"{key:<{key_width}}: {value}")


def print_status_table(data: dict, title: str = "Status") -> None:
    """Print a formatted status table."""
    print(f"\n{title}")
    print("-" * 40)
    max_key_len = max(len(str(k)) for k in data.keys()) if data else 10
    for key, value in data.items():
        print(f"  {key:<{max_key_len + 2}}: {value}")
    print()


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: Message to display
        default: Default value if user presses Enter

    Returns:
        True if confirmed, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    response = input(f"{message} [{default_str}]: ").strip().lower()

    if not response:
        return default
    return response in ("y", "yes")


def get_user_choice(
    prompt: str,
    options: list,
    allow_cancel: bool = True,
) -> Optional[int]:
    """
    Get user choice from numbered options.

    Args:
        prompt: Prompt message
        options: List of option descriptions
        allow_cancel: Whether to allow cancellation (0 or empty)

    Returns:
        Selected index (0-based) or None if cancelled
    """
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    if allow_cancel:
        print("  [0] Cancel")
    print()

    while True:
        try:
            response = input("Enter your choice: ").strip()
            if not response and allow_cancel:
                return None
            if response == "0" and allow_cancel:
                return None

            choice = int(response)
            if 1 <= choice <= len(options):
                return choice - 1
            print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print("Please enter a valid number")


class Timer:
    """Context manager for timing operations."""

    def __init__(self, description: str = "Operation"):
        self.description = description
        self.start_time: float = 0
        self.elapsed: float = 0

    def __enter__(self) -> "Timer":
        self.start_time = time.time()
        return self

    def __exit__(self, *args) -> None:
        self.elapsed = time.time() - self.start_time

    def __str__(self) -> str:
        return f"{self.description}: {format_duration(self.elapsed)}"


def batch_iterator(
    items: list,
    batch_size: int,
    desc: str = "Batches",
    show_progress: bool = True,
) -> Iterator[list]:
    """
    Iterate over items in batches.

    Args:
        items: List of items to batch
        batch_size: Size of each batch
        desc: Description for progress bar
        show_progress: Whether to show progress bar

    Yields:
        Batches of items
    """
    total_batches = (len(items) + batch_size - 1) // batch_size

    for i in range(0, len(items), batch_size):
        batch_num = i // batch_size + 1
        if show_progress:
            print(f"\r{desc}: batch {batch_num}/{total_batches}", end="", flush=True)
        yield items[i : i + batch_size]

    if show_progress:
        print()  # New line after progress
