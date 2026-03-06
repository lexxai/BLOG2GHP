from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Sequence

from blog_sync.config import BASE_DIR, POSTS_DIR


_slug_invalid_chars = re.compile(r"[^\w\s-]", re.UNICODE)
_slug_whitespace = re.compile(r"\s+")


def slugify(title: str) -> str:
    """Create a filesystem-friendly slug from a post title."""
    cleaned = _slug_invalid_chars.sub("", title).strip().lower()
    return _slug_whitespace.sub("-", cleaned)


def generate_post_path_name(date: datetime, title: str) -> str:
    """
    Build a Jekyll-compatible post filename:
        YYYY-MM-DD-slug.md
    """
    slug = slugify(title)
    return f"{date.strftime('%Y-%m-%d')}-{slug}.md"


def generate_post_filename(date: datetime, title: str) -> Path:
    """
    Build a Jekyll-compatible post filename:
        YYYY-MM-DD-slug.md
    """
    name = generate_post_path_name(date, title)
    return POSTS_DIR / name


def _format_tags(tags: Sequence[str]) -> str:
    """
    Format tags as a YAML inline list:
        ["tag1", "tag2"]
    """
    escaped = [f'"{t}"' for t in tags]
    return f"[{', '.join(escaped)}]"


def build_frontmatter(
    title: str,
    date: datetime,
    tags: Sequence[str],
    original_link: str,
) -> str:
    """
    Construct the YAML front matter for a post.
    """
    safe_title = title.replace('"', r"\"")
    tags_yaml = _format_tags(tags)
    date_str = date.strftime("%Y-%m-%d %H:%M:%S %z")

    frontmatter = f"""---
layout: post
title: "{safe_title}"
date: {date_str}
tags: {tags_yaml}
blogger_orig_link: {original_link}
---

"""
    return frontmatter


def write_post(
    filename: Path,
    frontmatter: str,
    body_markdown: str,
    *,
    dry_run: bool = False,
) -> Path:
    """
    Write the post Markdown file to disk under the repository root.

    Returns the absolute path to the file.
    """
    target_path = BASE_DIR / filename
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        content = f"{frontmatter}{body_markdown}".rstrip() + "\n"
        target_path.write_text(content, encoding="utf-8")

    return target_path


__all__ = [
    "slugify",
    "generate_post_filename",
    "build_frontmatter",
    "write_post",
]
