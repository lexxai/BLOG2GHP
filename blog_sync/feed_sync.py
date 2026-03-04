from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

from blog_sync.config import (
    PAGE_SIZE,
    RSS_URL,
    SAFETY_LIMIT,
    USE_THREADING,
    USE_THREADING,
    ensure_directories,
    get_rss_url,
)
from blog_sync.client import http_connection
from blog_sync.posts import (
    build_frontmatter,
    generate_post_filename,
    write_post,
)
from blog_sync.transform import transform_entry_html


from httpx import Client

from lxml import etree  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class ParsedEntry:
    title: str
    link: str
    published: str
    description: str
    tags: list[str]


class FeedSync:
    DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"

    """Main synchronization logic for fetching the RSS feed and generating Markdown posts."""

    def __init__(
        self,
        client: Client,
        dest: Path | None = None,
        limit: int | None = None,
        dry_run: bool = False,
        verbose: bool = False,
        use_threading: bool | None = None,
    ) -> None:
        self.client = client
        self.dest = dest
        self.limit = limit
        self.dry_run = dry_run
        self.verbose = verbose
        self.use_threading: bool = use_threading or USE_THREADING
        self.base_path = Path() if self.dest is None else self.dest

    def fetch_feed(self, url: str, client: Client | None = None) -> list[ParsedEntry]:
        """
        Fetch and parse the RSS feed using httpx + lxml.

        This is tailored for Blogger's RSS structure:
        <rss><channel><item>...</item></channel></rss>
        """
        client = client or self.client
        if client is None:
            assert ValueError("Client undefined")
            return []

        response = client.get(url)
        response.raise_for_status()

        root = etree.fromstring(response.content)

        entries: list[ParsedEntry] = []
        for item in root.xpath("//channel/item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()

            # Blogger labels appear as <category term="Label" .../>
            tags = [c.get("term") for c in item.findall("category") if c.get("term")]

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

    def _parse_date(self, entry: ParsedEntry) -> datetime:
        """Parse the published date from a parsed entry."""
        raw = entry.published or datetime.now().strftime(self.DATE_FORMAT)
        return datetime.strptime(raw, self.DATE_FORMAT)

    def _extract_tags(self, entry: ParsedEntry) -> list[str]:
        """Return tags/labels for an entry."""
        return entry.tags

    def process_entry(self, entry: ParsedEntry) -> None:
        date = self._parse_date(entry)
        filename = (self.base_path / generate_post_filename(date, entry.title)).resolve()

        if self.verbose:
            logger.info(f"Processing: {entry.title} -> {filename}")

        soup, md_body = transform_entry_html(entry.description, dest=self.base_path, client=self.client)
        tags = self._extract_tags(entry)

        frontmatter = build_frontmatter(
            title=entry.title,
            date=date,
            tags=tags,
            original_link=entry.link,
        )

        written_path = write_post(filename, frontmatter, md_body, dry_run=self.dry_run)

        if self.verbose:
            action = "Would write" if self.dry_run else "Wrote"
            logger.info(f"{action} post: {written_path}")

    def process_sync(self) -> None:
        """Fetch the RSS feed and generate/update Markdown posts."""

        start_index: int = 1
        max_per_page: int = int(PAGE_SIZE) if PAGE_SIZE.isdigit() else 50
        all_processed: bool = False

        ensure_directories(self.base_path)

        if self.client is None:
            raise ValueError("Client is required")

        total_processed = 0

        while not all_processed:

            rss_url = get_rss_url(start_index=start_index, max_results=max_per_page)

            if self.verbose:
                logger.debug(f"**** Fetching feed: {rss_url}")

            entries = self.fetch_feed(rss_url)

            if self.limit is not None and total_processed > self.limit:
                logger.info(f"Reached overall limit of {self.limit} entries. Stopping.")
                all_processed = True
                break

            if not entries:
                all_processed = True
                break
            if self.limit is not None:
                remaining = self.limit - total_processed
                fetched_entries = len(entries)
                if remaining < 0:
                    remaining = 0
                if remaining < fetched_entries:
                    entries = entries[:remaining]
                if len(entries) == 0:
                    all_processed = True
                    logger.info(f"Reached overall limit of {self.limit} entries. Stopping.")
                    break
                logger.debug(f"Fetched {fetched_entries} entries, processed {total_processed + len(entries)} so far.")

            for entry in entries:
                if self.dry_run:
                    logger.info(f"Would process entry: {entry.title}")
                else:
                    self.process_entry(entry)

            # Move to the next page
            start_index += len(entries)
            total_processed += len(entries)

            # Safety break if needed
            if start_index > SAFETY_LIMIT:  # Adjust based on your total post count
                logger.warning(f"Reached safety limit for pagination ({SAFETY_LIMIT}). Stopping.")
                break
