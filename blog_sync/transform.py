from __future__ import annotations

from pathlib import Path
import re
from typing import Tuple

from bs4 import BeautifulSoup
import markdownify

from blog_sync.config import OLD_DOMAIN, NEW_DOMAIN
from blog_sync.downloader import download_image


_domain_pattern = re.compile(rf"^(https?:)?//{re.escape(OLD_DOMAIN)}", re.IGNORECASE)


def _rewrite_images(soup: BeautifulSoup, dest: Path, client) -> None:
    """Download images and rewrite their src attributes to local paths."""
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        new_src = download_image(str(src), base_path=dest, client=client)
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


def _extract_image_tables(soup):
    """Convert Blogger image tables to cleaner figure+caption format."""

    tables_to_replace = []

    for table in soup.find_all("table"):
        tbody = table.find("tbody")
        if not tbody:
            continue

        rows = tbody.find_all("tr", recursive=False)

        if len(rows) == 2:
            img = rows[0].find("img")
            caption_td = rows[1].find("td", class_="tr-caption")

            if img and caption_td:
                # Create figure
                figure = soup.new_tag("figure")

                # Get the link or just the img
                link = rows[0].find("a")
                if link:
                    new_link = soup.new_tag("a", href=link.get("href"))
                    new_img = soup.new_tag("img", src=img.get("src"), alt=img.get("alt", ""))
                    new_link.append(new_img)
                    figure.append(new_link)
                else:
                    new_img = soup.new_tag("img", src=img.get("src"), alt=img.get("alt", ""))
                    figure.append(new_img)

                # Add caption
                figcaption = soup.new_tag("figcaption")
                figcaption.string = caption_td.get_text(strip=True)
                figure.append(figcaption)

                tables_to_replace.append((table, figure))

    # Replace all at once to avoid iteration issues
    for table, figure in tables_to_replace:
        table.replace_with(figure)





def md(soup, **options):
    return markdownify.MarkdownConverter(**options).convert_soup(soup)


def analyze_blogger_images(soup):
    """Fetch and analyze image table structures from Blogger."""

    # Find all tables
    tables = soup.find_all("table")
    print(f"Found {len(tables)} tables\n")

    for i, table in enumerate(tables, 1):
        print(f"=== TABLE {i} ===")
        tbody = table.find("tbody")
        if not tbody:
            print("  No tbody\n")
            continue

        rows = tbody.find_all("tr", recursive=False)
        print(f"  Rows: {len(rows)}")

        for j, row in enumerate(rows, 1):
            print(f"  Row {j}:")
            img = row.find("img")
            caption = row.find("td", class_="tr-caption")
            print(f"    - Has img: {img is not None}")
            print(f"    - Has caption: {caption is not None}")
            if caption:
                print(f"    - Caption text: {caption.get_text(strip=True)}")
        print()


def transform_entry_html(html: str, dest: Path, client) -> Tuple[BeautifulSoup, str]:
    """
    Parse an entry's HTML, download/rewire images and links, and
    return both the BeautifulSoup tree and its Markdown representation.
    """
    soup = BeautifulSoup(html, "html.parser")

    _extract_image_tables(soup)
    _rewrite_images(soup, dest=dest, client=client)
    _rewrite_internal_links(soup)

    # md_body = markdownify.markdownify(str(soup), heading_style="ATX")
    md_body = md(
        soup,
        heading_style="ATX",  # Use # headers
        # keep_inline_images_in=["td", "table"]
    )

    return soup, md_body


__all__ = ["transform_entry_html"]
