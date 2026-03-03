from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

import httpx

from .config import BASE_DIR, IMG_DIR


def _stable_filename_from_url(url: str, fallback_ext: str = ".jpg") -> str:
    """
    Build a reasonably stable filename from the URL.

    - Prefer the basename of the path when it has an extension.
    - Otherwise, use a short hash of the URL with a fallback extension.
    """
    path = Path(url.split("?", 1)[0])
    name = path.name
    if name and "." in name:
        return name

    digest = hashlib.blake2b(url.encode("utf-8")).hexdigest()[:16]
    return f"img_{digest}{fallback_ext}"


def download_image(img_url: str, timeout: int = 15) -> str:
    """
    Download an image and return the web path relative to the site root.

    On success:
        returns a path like '/assets/images/blog/filename.ext'
    On failure:
        returns the original `img_url` so the HTML still points somewhere.
    """
    try:
        filename = _stable_filename_from_url(img_url)
        local_dir: Path = BASE_DIR / IMG_DIR
        local_dir.mkdir(parents=True, exist_ok=True)

        local_path: Path = local_dir / filename
        web_path = f"/{IMG_DIR.as_posix()}/{filename}"

        if not local_path.exists():
            response = httpx.get(img_url, timeout=timeout)
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(response.content)

        return web_path
    except Exception:
        # Fallback to original URL if anything goes wrong.
        return img_url


__all__ = ["download_image"]

