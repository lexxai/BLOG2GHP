from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence

import httpx
from lxml import etree

from blog_sync.config import RSS_URL, ensure_directories
from blog_sync.posts import (
    build_frontmatter,
    generate_post_filename,
    write_post,
)
from blog_sync.transform import transform_entry_html


DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"


@dataclass
class ParsedEntry:
    title: str
    link: str
    published: str
    description: str
    tags: List[str]


def fetch_feed(url: str) -> List[ParsedEntry]:
    """
    Fetch and parse the RSS feed using httpx + lxml.

    This is tailored for Blogger's RSS structure:
      <rss><channel><item>...</item></channel></rss>
    """
    response = httpx.get(url, timeout=15)
    response.raise_for_status()

    root = etree.fromstring(response.content)

    entries: List[ParsedEntry] = []
    for item in root.xpath("//channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()

        # Blogger labels appear as <category term="Label" .../>
        tags = [
            c.get("term")
            for c in item.findall("category")
            if c.get("term")
        ]

        entries.append(
            ParsedEntry(
                title=title,
                link=link,
                published=published,
                description=description,
                tags=tags,
            )
        )

    return entries


def _parse_date(entry: ParsedEntry) -> datetime:
    """Parse the published date from a parsed entry."""
    raw = entry.published or datetime.now().strftime(DATE_FORMAT)
    return datetime.strptime(raw, DATE_FORMAT)


def _extract_tags(entry: ParsedEntry) -> Sequence[str]:
    """Return tags/labels for an entry."""
    return entry.tags


def process_sync(*, limit: int | None = None, dry_run: bool = False, verbose: bool = False) -> None:
    """Fetch the RSS feed and generate/update Markdown posts."""
    ensure_directories()

    if verbose:
        print(f"Fetching feed: {RSS_URL}")

    entries = fetch_feed(RSS_URL)

    if limit is not None:
        entries = entries[:limit]

    for entry in entries:
        date = _parse_date(entry)
        filename = generate_post_filename(date, entry.title)

        if verbose:
            print(f"Processing: {entry.title} -> {filename}")

        soup, md_body = transform_entry_html(entry.description)
        tags = _extract_tags(entry)

        frontmatter = build_frontmatter(
            title=entry.title,
            date=date,
            tags=tags,
            original_link=entry.link,
        )

        written_path = write_post(filename, frontmatter, md_body, dry_run=dry_run)

        if verbose:
            action = "Would write" if dry_run else "Wrote"
            print(f"{action} post: {written_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync Blogger RSS feed to a GitHub Pages/Jekyll repository.",
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
    process_sync(
        limit=args.limit,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()

