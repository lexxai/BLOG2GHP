import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _get_env(name: str, default: str) -> str:
    """Return environment variable or default."""
    return os.environ.get(name, default)


# --- CONFIGURATION (can be overridden via env vars) ---

LOG_LEVEL: str = _get_env("LOG_LEVEL", "INFO")
MAX_RESULTS: str = _get_env("MAX_RESULTS", "50")
BASE_URL: str = _get_env("BASE_URL", "lexxai.blogspot.com")


RSS_URL: str = _get_env(
    "BLOG_RSS_URL",
    f"https://{BASE_URL}/feeds/posts/default?alt=rss&max-results={MAX_RESULTS}",
)

OLD_DOMAIN: str = _get_env("BLOG_OLD_DOMAIN", BASE_URL)
NEW_DOMAIN: str = _get_env("BLOG_NEW_DOMAIN", f"{OLD_DOMAIN.split('.')[0]}.github.io")

# Content/output paths (relative to repo root)
POSTS_DIR: Path = Path(_get_env("BLOG_POSTS_DIR", "_posts"))
IMG_DIR: Path = Path(_get_env("BLOG_IMG_DIR", "assets/images/blog"))


def ensure_directories() -> None:
    """Create required local directories if they do not exist."""
    (BASE_DIR / POSTS_DIR).mkdir(parents=True, exist_ok=True)
    (BASE_DIR / IMG_DIR).mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """Setup logging with colored output."""
    try:
        import coloredlogs

        coloredlogs.install(
            level=getattr(logging, LOG_LEVEL.upper()),
            fmt="%(asctime)s - %(levelname)s - %(message)s",
        )
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL.upper()),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    logging.getLogger("httpx").setLevel(logging.WARNING)


setup_logging()


__all__ = [
    "BASE_DIR",
    "RSS_URL",
    "OLD_DOMAIN",
    "NEW_DOMAIN",
    "POSTS_DIR",
    "IMG_DIR",
    "ensure_directories",
]
