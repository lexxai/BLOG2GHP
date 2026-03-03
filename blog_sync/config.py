import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env(name: str, default: str) -> str:
    """Return environment variable or default."""
    return os.environ.get(name, default)


# --- CONFIGURATION (can be overridden via env vars) ---

RSS_URL: str = _get_env(
    "BLOG_RSS_URL",
    "https://lexxai.blogspot.com/feeds/posts/default?alt=rss&max-results=500",
)

OLD_DOMAIN: str = _get_env("BLOG_OLD_DOMAIN", "lexxai.blogspot.com")
NEW_DOMAIN: str = _get_env("BLOG_NEW_DOMAIN", "lexxai.github.io")

# Content/output paths (relative to repo root)
POSTS_DIR: Path = Path(
    _get_env("BLOG_POSTS_DIR", "_posts")
)
IMG_DIR: Path = Path(
    _get_env("BLOG_IMG_DIR", "assets/images/blog")
)


def ensure_directories() -> None:
    """Create required local directories if they do not exist."""
    (BASE_DIR / POSTS_DIR).mkdir(parents=True, exist_ok=True)
    (BASE_DIR / IMG_DIR).mkdir(parents=True, exist_ok=True)


__all__ = [
    "BASE_DIR",
    "RSS_URL",
    "OLD_DOMAIN",
    "NEW_DOMAIN",
    "POSTS_DIR",
    "IMG_DIR",
    "ensure_directories",
]

