from __future__ import annotations

import re
from typing import Tuple

from bs4 import BeautifulSoup
import markdownify

from .config import OLD_DOMAIN, NEW_DOMAIN
from .downloader import download_image


_domain_pattern = re.compile(rf"^(https?:)?//{re.escape(OLD_DOMAIN)}", re.IGNORECASE)


def _rewrite_images(soup: BeautifulSoup) -> None:
    """Download images and rewrite their src attributes to local paths."""
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        new_src = download_image(src)
        img["src"] = new_src


def _rewrite_internal_links(soup: BeautifulSoup) -> None:
    """
    Rewrite links that point to the old domain so that they use the new domain.

    Handles:
        - http://OLD_DOMAIN/...
        - https://OLD_DOMAIN/...
        - //OLD_DOMAIN/...
    """
    for a in soup.find_all("a", href=True):
        href = a["href"]
        match = _domain_pattern.match(href)
        if not match:
            continue

        # Preserve path/query after the domain and normalize to https://NEW_DOMAIN
        rest = href[match.end() :]
        a["href"] = f"https://{NEW_DOMAIN}{rest}"


def transform_entry_html(html: str) -> Tuple[BeautifulSoup, str]:
    """
    Parse an entry's HTML, download/rewire images and links, and
    return both the BeautifulSoup tree and its Markdown representation.
    """
    soup = BeautifulSoup(html, "html.parser")

    _rewrite_images(soup)
    _rewrite_internal_links(soup)

    md_body = markdownify.markdownify(str(soup), heading_style="ATX")
    return soup, md_body


__all__ = ["transform_entry_html"]
