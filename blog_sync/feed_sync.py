from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

from blog_sync.config import RSS_URL, ensure_directories
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
    ) -> None:
        self.client = client
        self.dest = dest
        self.limit = limit
        self.dry_run = dry_run
        self.verbose = verbose

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

    def process_sync(self) -> None:
        """Fetch the RSS feed and generate/update Markdown posts."""

        base_path = Path() if self.dest is None else self.dest

        ensure_directories(base_path)

        if self.verbose:
            logger.info(f"Fetching feed: {RSS_URL}")

        if self.client is None:
            raise ValueError("Client is required")

        entries = self.fetch_feed(RSS_URL)

        if self.limit is not None:
            entries = entries[:self.limit]

        for entry in entries:
            date = self._parse_date(entry)
            filename = (base_path / generate_post_filename(date, entry.title)).resolve()

            if self.verbose:
                logger.info(f"Processing: {entry.title} -> {filename}")

            soup, md_body = transform_entry_html(entry.description, dest=base_path, client=self.client)
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
