from httpx import Client, HTTPTransport


class HttpConnection:

    def __init__(self) -> None:
        self.client: Client | None = None
        self.options = {
            "retries": 10,
            "timeout": 15,
            "http2": True,
            "follow_redirects": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def get_client(self) -> Client:
        if self.client is None:
            self.client = Client(
                timeout=self.options["timeout"],
                headers={
                    "User-Agent": self.options["user_agent"],
                },
                follow_redirects=self.options["follow_redirects"],
                http2=self.options["http2"],
                transport=HTTPTransport(retries=self.options["retries"]),
            )
        return self.client

    def re_connect(self):
        self.close()
        return self.get_client()

    def close(self):
        if self.client is None:
            return
        self.client.close()
        self.client = None


http_connection: HttpConnection = HttpConnection()
