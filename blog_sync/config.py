import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.resolve()


def _get_env(name: str, default: str) -> str:
    """Return environment variable or default."""
    return os.environ.get(name, default)


# --- CONFIGURATION (can be overridden via env vars) ---

LOG_LEVEL: str = _get_env("LOG_LEVEL", "INFO")
MAX_RESULTS: str | None = os.environ.get("MAX_RESULTS")
PAGE_SIZE: str = _get_env("PAGE_SIZE", "50")
BASE_URL: str = _get_env("BASE_URL", "lexxai.blogspot.com")
SAFETY_LIMIT = 5_000  # Max entries to process in total (to prevent infinite loops)

USE_THREADING: bool = _get_env("USE_THREADING", "true").lower() in ("true", "1", "yes")
MAX_THREADS_WORKERS: int = int(_get_env("MAX_THREADS_WORKERS", "10"))


RSS_URL: str = _get_env(
    "BLOG_RSS_URL",
    f"https://{BASE_URL}/feeds/posts/default?alt=rss",
)

ENABLE_REWRITE_LINKS: bool = _get_env("ENABLE_REWRITE_LINKS", "false").lower() in ("true", "1", "yes")
OLD_DOMAIN: str = _get_env("BLOG_OLD_DOMAIN", BASE_URL)
NEW_DOMAIN: str = _get_env("BLOG_NEW_DOMAIN", f"{OLD_DOMAIN.split('.')[0]}.github.io")

# Content/output paths (relative to repo root)
POSTS_DIR: Path = Path(_get_env("BLOG_POSTS_DIR", "_posts"))
IMG_DIR: Path = Path(_get_env("BLOG_IMG_DIR", "assets/images/blog"))


def get_rss_url(start_index: int = 1, max_results: int | None = None) -> str:
    """Construct the RSS feed URL with pagination parameters."""
    return f"{RSS_URL}&max-results={max_results or PAGE_SIZE}&start-index={start_index}"


def ensure_directories(base_path: Path) -> None:
    """Create required local directories if they do not exist."""
    (BASE_DIR / base_path / POSTS_DIR).mkdir(parents=True, exist_ok=True)
    (BASE_DIR / base_path / IMG_DIR).mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """Setup logging with colored output."""
    try:
        import coloredlogs

        coloredlogs.install(
            level=getattr(logging, LOG_LEVEL.upper()),
            fmt="%(asctime)s - %(levelname)s - %(message)s",  # %(name)s
        )
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL.upper()),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


setup_logging()
