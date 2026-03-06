from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from threading import Lock

import orjson

from blog_sync.config import (
    MAX_THREADS_WORKERS,
    PAGE_SIZE,
    SAFETY_LIMIT,
    USE_THREADING,
    ensure_directories,
    get_rss_url,
    BUILD_HISTORY_TREE_DEPTH,
    BUILD_HISTORY_TREE_ENABLE,
    BASE_DIR,
    HISTORY_TREE_DIR,
)
from blog_sync.posts import (
    build_frontmatter,
    generate_post_filename,
    write_post,
    generate_post_path_name,
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
        self.max_workers = MAX_THREADS_WORKERS
        self.build_history_tree_depth = BUILD_HISTORY_TREE_DEPTH
        self.build_history_tree_enable = BUILD_HISTORY_TREE_ENABLE
        self.history_data_file: Path = BASE_DIR / self.base_path / HISTORY_TREE_DIR / "history.json"
        self.history_tree_data = self.load_history_data()
        self.history_tree_data_size = len(self.history_tree_data)
        self.lock = Lock()

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
            tags = [text for c in item.findall("category") if (text:=c.text.strip())]

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

        soup, md_body = transform_entry_html(
            entry.description, dest=self.base_path, client=self.client, use_threading=self.use_threading, history_tree_data=self.history_tree_data
        )
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

    def get_entry_rewritten_link(self, entry: ParsedEntry) -> tuple[str, str]:
        date = self._parse_date(entry)
        filename = generate_post_path_name(date, entry.title)
        original_link = entry.link
        new_link = f"/{filename}"
        return original_link, new_link

    def process_sync(self) -> None:
        """Fetch the RSS feed and generate/update Markdown posts."""

        start_index: int = 1
        max_per_page: int = int(PAGE_SIZE) if PAGE_SIZE.isdigit() else 50
        all_processed: bool = False

        ensure_directories(self.base_path)

        if self.client is None:
            raise ValueError("Client is required")

        if self.history_tree_data_size == 0:
            self.process_history_build()
        else:
            self.process_history_build(depth=self.limit)

        total_processed = 0

        if self.limit < max_per_page:
            max_per_page = self.limit

        while not all_processed:
            rss_url = get_rss_url(start_index=start_index, max_results=max_per_page)

            if self.verbose:
                logger.debug(f"**** Fetching feed: {rss_url}")

            try:
                entries = self.fetch_feed(rss_url)
            except Exception as e:
                logger.error(f"Error fetching feed {rss_url}: {e}")
                continue

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

            if self.use_threading:
                from concurrent.futures import ThreadPoolExecutor

                logger.debug(f"Processing {len(entries)} entries with threading (max_workers={self.max_workers})...")
                # Create a list of futures to process the entries concurrently
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    executor.map(self.process_entry, entries)
                self.processing_entries_for_history(entries)
            else:
                for entry in entries:
                    if self.dry_run:
                        logger.info(f"Would process entry: {entry.title}")
                    else:
                        self.process_entry(entry)
                        self.processing_entries_for_history([entry])

            # Move to the next page
            start_index += len(entries)
            total_processed += len(entries)

            # Safety break if needed
            if start_index > SAFETY_LIMIT:  # Adjust based on your total post count
                logger.warning(f"Reached safety limit for pagination ({SAFETY_LIMIT}). Stopping.")
                break

        self.save_history_data()

    def load_history_data(self, history_data_file: Path = None) -> dict:
        history_data_file = history_data_file or self.history_data_file
        ensure_directories(self.base_path)
        if history_data_file.exists():
            logger.info(f"Loading history file: {history_data_file}")
            try:
                data = orjson.loads(history_data_file.read_bytes())
                logger.info(f"Loaded {len(data)} history entries")
                return data
            except Exception as e:
                logger.error(f"Error load history data {history_data_file}: {e}")
        return {}

    def save_history_data(self, data: dict = None, history_data_file: Path = None):
        history_data_file = history_data_file or self.history_data_file
        history_data_file_tmp = history_data_file.with_suffix(".tmp")
        data = data or self.history_tree_data
        if not data:
            logger.info("No data to save")
            return
        len_data = len(data)
        if len_data <= self.history_tree_data_size:
            logger.info("No changes to save")
            return
        logger.info(f"Saving history data for a new {len_data - self.history_tree_data_size} records")
        ensure_directories(self.base_path)
        if history_data_file.exists():
            try:
                history_data_file_tmp.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
                history_data_file_tmp.replace(history_data_file)
                self.history_tree_data_size = len_data
            except Exception as e:
                logger.error(f"Error save history data {history_data_file_tmp}: {e}")
        else:
            try:
                history_data_file.write_bytes(orjson.dumps(data))
                self.history_tree_data_size = len_data
            except Exception as e:
                logger.error(f"Error save history data {history_data_file}: {e}")
        logger.info(f"Saved history data to {history_data_file}")

    def processing_entries_for_history(self, entries):
        for entry in entries:
            original_link, new_link = self.get_entry_rewritten_link(entry)
            if self.dry_run:
                logger.debug(f"Would process entry with original link: {original_link} {new_link}")
                continue
            # else:
                # logger.debug(f"Processing entry with original link: {original_link} {new_link}")

            if original_link and new_link and original_link not in self.history_tree_data:
                self.history_tree_data[original_link] = new_link

    def process_history_build(self, depth: int = None) -> None:

        if not self.build_history_tree_enable:
            logger.info("Build history tree is disabled. Skipping.")
            return

        start_index: int = 1
        max_per_page: int = int(PAGE_SIZE) if PAGE_SIZE.isdigit() else 50
        all_processed: bool = False

        if self.client is None:
            raise ValueError("Client is required")

        total_processed = 0

        limit = depth or self.build_history_tree_depth
        if limit < max_per_page:
            max_per_page = limit

        while not all_processed:
            rss_url = get_rss_url(start_index=start_index, max_results=max_per_page)

            if self.verbose:
                logger.debug(f"**** Fetching feed for history build: {rss_url}")

            try:
                entries = self.fetch_feed(rss_url)
            except Exception as e:
                logger.error(f"Error fetching feed {rss_url}: {e}")
                continue

            if limit is not None and total_processed > limit:
                logger.info(f"Reached overall limit of {limit} entries. Stopping.")
                all_processed = True
                break

            if not entries:
                all_processed = True
                break
            if limit is not None:
                remaining = limit - total_processed
                fetched_entries = len(entries)
                if remaining < 0:
                    remaining = 0
                if remaining < fetched_entries:
                    entries = entries[:remaining]
                if len(entries) == 0:
                    all_processed = True
                    logger.info(f"Reached overall limit of {limit} entries. Stopping.")
                    break
                logger.debug(f"Fetched {fetched_entries} entries, processed {total_processed + len(entries)} so far.")

            self.processing_entries_for_history(entries)

            # Move to the next page
            start_index += len(entries)
            total_processed += len(entries)

            # Safety break if needed
            if start_index > SAFETY_LIMIT:  # Adjust based on your total post count
                logger.warning(f"Reached safety limit for pagination ({SAFETY_LIMIT}). Stopping.")
                break

        self.save_history_data()
