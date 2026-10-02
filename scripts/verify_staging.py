"""Read-only rollout verification: an accepted hook alone is not a deployment."""

import os
import re
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BuildIdentity(HTMLParser):
    def __init__(self):
        super().__init__()
        self.commit = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "meta" and attributes.get("name") == "agrochain-build":
            self.commit = attributes.get("content")


def main():
    expected = os.environ["EXPECTED_COMMIT"]
    if not re.fullmatch(r"[a-fA-F0-9]{40}", expected):
        raise SystemExit("EXPECTED_COMMIT must be a full commit SHA.")

    deadline = time.monotonic() + 300
    frontend = "https://ttcs-frontend-staging.onrender.com/"
    backend = "https://ttcs-backend-staging.onrender.com/"
    while time.monotonic() < deadline:
        try:
            request = Request(frontend, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                html = response.read(1_000_000).decode("utf-8")
            identity = BuildIdentity()
            identity.feed(html)
            if identity.commit == expected:
                with urlopen(backend, timeout=20) as response:
                    if response.status == 200:
                        print(f"Verified frontend commit {expected} and API HTTP 200.")
                        return
            print(f"Waiting for {expected[:12]}; domain serves {identity.commit or 'an unstamped build'}.")
        except (HTTPError, URLError, TimeoutError, UnicodeDecodeError) as error:
            print(f"Waiting for staging: {type(error).__name__}.")
        time.sleep(10)

    raise SystemExit(
        "Staging did not serve the expected commit within 5 minutes. "
        "Check the Render service linked repository, branch, build command and deploy logs."
    )


if __name__ == "__main__":
    main()
