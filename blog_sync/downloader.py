from __future__ import annotations

import hashlib
import logging
from urllib.parse import urlsplit
from pathlib import Path

from httpx import Client

from blog_sync.config import BASE_DIR, IMG_DIR

logger = logging.getLogger(__name__)


def str_hash(data: str) -> str:
    return hashlib.blake2b(data.encode()).hexdigest()[:16]


def _stable_filename_from_url(url: str, fallback_ext: str = ".jpg") -> str:
    """
    Build a reasonably stable filename from the URL.

    - Prefer the basename of the path when it has an extension.
    - Otherwise, use a short hash of the URL with a fallback extension.
    """

    urlparts = urlsplit(url)
    path = urlparts.path
    image_path = Path(path)
    digest_parent = str_hash(str(image_path.parent))
    # logger.debug(image_path)
    image_ext = image_path.suffix or fallback_ext
    filename = image_path.with_suffix(image_ext.lower())
    digest_name = str_hash(filename.name)
    return f"{digest_parent}-{filename.with_stem(digest_name).name}"


def download_image(img_url: str, base_path: Path, timeout: int = 15, client: Client | None = None) -> str | None:
    """
    Download an image and return the web path relative to the site root.

    On success:
        returns a path like '/assets/images/blog/filename.ext'
    On failure:
        returns the original `img_url` so the HTML still points somewhere.
    """
    if client is None:
        assert ValueError("client must be provided")
        return

    try:
        filename = _stable_filename_from_url(img_url)
        local_dir: Path = (BASE_DIR / base_path / IMG_DIR).resolve()
        local_dir.mkdir(parents=True, exist_ok=True)

        local_path: Path = local_dir / filename
        web_path = f"/{IMG_DIR.as_posix()}/{filename}"

        if not local_path.exists():
            response = client.get(img_url, timeout=timeout)
            if response.status_code == 200:
                logger.debug(f"download_image to {local_path}")
                with open(local_path, "wb") as f:
                    f.write(response.content)

        return web_path
    except Exception:
        # Fallback to original URL if anything goes wrong.
        return img_url


__all__ = [
    "download_image",
]
