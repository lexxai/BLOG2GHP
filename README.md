# blog2ghp - Blogger to GitHub Pages Sync Tool

A Python utility that syncs posts from a Blogger RSS feed to a GitHub Pages/Jekyll repository. It automatically downloads images, rewrites internal links, and generates properly formatted Markdown files with frontmatter.

## Features

- **Automated Sync**: Fetches posts from Blogger RSS feeds
- **Image Handling**: Downloads blog images and stores them locally in `assets/images/blog/`
- **Link Rewriting**: Updates old domain links to point to your new GitHub Pages URL
- **Jekyll-compatible Output**: Generates Markdown files with proper YAML frontmatter
- **Dry Run Mode**: Preview changes without writing files
- **Configurable**: Easy configuration via environment variables

## Requirements

- Python 3.12+
- pip/uv

## Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
# Blogger feed URL
BLOG_RSS_URL=https://yourblog.blogspot.com/feeds/posts/default?alt=rss&max-results=50

# Your current blog domain (for link rewriting)
BLOG_OLD_DOMAIN=yourblog.blogspot.com

# Your GitHub Pages domain
BLOG_NEW_DOMAIN=yourusername.github.io

# Number of posts to sync per run
MAX_RESULTS=50

# Optional: Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

## Usage

### Basic Sync

```bash
python -m blog2ghp.sync_blog --verbose
```

### Dry Run (Preview Changes)

```bash
python -m blog2ghp.sync_blog --dry-run --verbose
```

### Limit Results

```bash
# Only sync the latest 10 posts
python -m blog2ghp.sync_blog --limit 10
```

## Project Structure

```
.
├── blog_sync/           # Main Python package
│   ├── __init__.py
│   ├── config.py        # Configuration and environment variables
│   ├── downloader.py    # HTTP client and image download utilities
│   ├── posts.py         # Markdown post generation and file writing
│   └── transform.py     # HTML to Markdown transformation with link/image rewriting
├── sync_blog.py         # Main entry point script
├── pyproject.toml       # Project configuration
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## How It Works

1. **Fetch RSS Feed**: Downloads your Blogger RSS feed
2. **Process Entries**: For each post:
   - Parses HTML content
   - Downloads all images with stable filenames
   - Rewrites old domain links to new GitHub Pages URL
   - Converts HTML to Markdown
3. **Generate Files**: Creates Jekyll-compatible Markdown files in `_posts/`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BLOG_RSS_URL` | Blogger RSS feed URL | Derived from BASE_URL |
| `BASE_URL` | Your blog domain (without http://) | lexxai.blogspot.com |
| `BLOG_OLD_DOMAIN` | Old domain for link rewriting | Same as BASE_URL |
| `BLOG_NEW_DOMAIN` | New GitHub Pages domain | {old-domain}.github.io |
| `MAX_RESULTS` | Posts to sync per run | 50 |
| `BLOG_POSTS_DIR` | Output directory for posts | _posts |
| `BLOG_IMG_DIR` | Output directory for images | assets/images/blog |
| `LOG_LEVEL` | Logging verbosity | INFO |

## Generated File Format

Each post is written as:

```markdown
---
layout: post
title: "Your Post Title"
date: 2024-01-15 10:30:00 +0000
tags: ["tech", "python"]
blogger_orig_link: https://old-domain.blogspot.com/...
---

[Content with local image paths]
```

## Logging

The tool uses colored logs (requires `coloredlogs` package). Set `LOG_LEVEL=DEBUG` for detailed progress.

## License

MIT License

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style (black, ruff)
- Tests are passing (if any exist)
- Documentation is updated