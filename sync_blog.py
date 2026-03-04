from __future__ import annotations

import argparse
import logging
from pathlib import Path


from blog_sync.client import http_connection
from blog_sync.feed_sync import FeedSync


logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync Blogger RSS feed to a GitHub Pages/Jekyll repository.",
    )
    parser.add_argument(
        "--dest",
        "-d",
        type=Path,
        default=None,
        help="Destination root folder for download",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the latest N entries from the feed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write any files, just print what would be done.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress information.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        with http_connection.get_client() as client:
            feed_sync = FeedSync(client, dest=args.dest, limit=args.limit, dry_run=args.dry_run, verbose=args.verbose)
            feed_sync.process_sync()
    except KeyboardInterrupt:
        logger.info("Keyboard Ctrl-C")


if __name__ == "__main__":
    main()
