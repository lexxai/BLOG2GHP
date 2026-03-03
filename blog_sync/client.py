import httpx


def get_client() -> httpx.Client:
    """Get a configured httpx client."""
    return httpx.Client(
        timeout=15,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        follow_redirects=True,
        http2=True,
        transport=httpx.HTTPTransport(retries=10),
    )
