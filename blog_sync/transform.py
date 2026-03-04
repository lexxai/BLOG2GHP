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
    
    for tbody in soup.find_all("tbody"):
        rows = tbody.find_all("tr")
        
        # Check if it's an image table (image row + caption row)
        if len(rows) == 2:
            img_cell = rows[0].find("img")
            caption_cell = rows[1].find("td", class_="tr-caption")
            
            if img_cell and caption_cell:
                # Create a cleaner structure
                figure = soup.new_tag("figure")
                
                # Keep the link if it exists
                link = rows[0].find("a")
                if link:
                    figure.append(link)
                else:
                    figure.append(img_cell)
                
                # Add caption
                figcaption = soup.new_tag("figcaption")
                figcaption.string = caption_cell.get_text(strip=True)
                figure.append(figcaption)
                
                # Replace table with figure
                tbody.parent.replace_with(figure)

def md(soup, **options):
    return markdownify.MarkdownConverter(**options).convert_soup(soup)


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
        keep_inline_images_in=["td"],  # Keep <img> tags inside <td>
        # convert=["img"],
    )

    return soup, md_body


__all__ = ["transform_entry_html"]
