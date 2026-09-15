"""Fetch a public web page on a visitor's behalf, without becoming a proxy.

Every SEO checker a visitor has used before takes a URL and fetches the page
itself. Asking them to paste HTML instead is what makes our versions look
broken, so we fetch — but a server that fetches whatever URL it is handed is a
Server-Side Request Forgery hole: it sits inside the network, so it can reach
things the visitor cannot. `http://169.254.169.254/` returns cloud credentials
on most providers, and `http://127.0.0.1:5432` is our own database.

The defence here is to resolve the hostname ourselves, refuse every address that
is not publicly routable, and then connect to that exact IP. Connecting to the
IP rather than the name is what closes the DNS-rebinding window, where a name
resolves to a public address for the check and a private one a moment later for
the connection.
"""
from __future__ import annotations

import ipaddress
import socket
import ssl
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse, urlunparse

MAX_BYTES = 4 * 1024 * 1024
TIMEOUT_SECONDS = 12
MAX_REDIRECTS = 5

# A real User-Agent. Many sites serve a blank page or a challenge to anything
# that looks like a script, and an identifying string is the polite way to say
# who is asking.
USER_AGENT = (
    "Mozilla/5.0 (compatible; ToolSimpliBot/1.0; +https://www.toolsimpli.com/) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


class FetchError(Exception):
    """The page could not be fetched, with a reason worth showing the visitor."""


def _public_address(host: str) -> tuple[str, int]:
    """Resolve a hostname and return one publicly routable address for it.

    Every address the name resolves to has to pass: a host with one public and
    one private record would otherwise be a way in, since which one is used is
    not ours to choose.
    """
    try:
        records = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise FetchError(f"Could not find {host} — check the address is right.") from exc
    if not records:
        raise FetchError(f"Could not find {host}.")

    chosen = None
    for family, _, _, _, sockaddr in records:
        address = sockaddr[0]
        try:
            ip = ipaddress.ip_address(address.split("%")[0])
        except ValueError:
            raise FetchError("That hostname resolved to something unreadable.") from None
        if not ip.is_global or ip.is_multicast:
            # is_global is false for loopback, private ranges, link-local
            # (169.254.x, where cloud metadata lives), CGNAT and reserved blocks.
            raise FetchError(
                "That address points inside a private network, so it will not be fetched. "
                "Enter a public URL, or paste the page's HTML instead."
            )
        if chosen is None:
            chosen = (address, family)
    if chosen is None:
        raise FetchError("That hostname has no usable address.")
    return chosen


def _request_once(url: str) -> tuple[int, dict, bytes, str | None]:
    """One HTTP request, with no redirect following."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError("Only http and https addresses can be fetched.")
    host = parts.hostname
    if not host:
        raise FetchError("That URL has no hostname.")

    address, family = _public_address(host)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = urlunparse(("", "", parts.path or "/", parts.params, parts.query, ""))

    if parts.scheme == "https":
        context = ssl.create_default_context()
        # Connect to the validated IP, but present and verify the certificate
        # against the real hostname — otherwise pinning to the IP would break TLS.
        connection = HTTPSConnection(address, port, timeout=TIMEOUT_SECONDS,
                                     context=context, blocksize=65536)
        connection.host = host
    else:
        connection = HTTPConnection(address, port, timeout=TIMEOUT_SECONDS, blocksize=65536)

    try:
        connection.putrequest("GET", path, skip_host=True, skip_accept_encoding=True)
        connection.putheader("Host", host if port in (80, 443) else f"{host}:{port}")
        connection.putheader("User-Agent", USER_AGENT)
        connection.putheader("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        connection.putheader("Accept-Language", "en-US,en;q=0.9")
        connection.putheader("Accept-Encoding", "identity")
        connection.putheader("Connection", "close")
        connection.endheaders()
        response = connection.getresponse()
        headers = {k.lower(): v for k, v in response.getheaders()}
        # Read with a ceiling rather than .read(): a huge or endless response
        # would otherwise be pulled entirely into memory.
        body = response.read(MAX_BYTES + 1)
        return response.status, headers, body, response.getheader("Location")
    except FetchError:
        raise
    except ssl.SSLCertVerificationError as exc:
        raise FetchError(f"That site's HTTPS certificate could not be verified: {exc.verify_message}") from exc
    except socket.timeout as exc:
        raise FetchError(f"{host} did not respond within {TIMEOUT_SECONDS} seconds.") from exc
    except OSError as exc:
        raise FetchError(f"Could not reach {host}: {exc}") from exc
    finally:
        connection.close()


def fetch_page(url: str) -> tuple[str, dict]:
    """Fetch a page and return its HTML plus a little about the response.

    Redirects are followed by hand so each hop is validated the same way as the
    first — a public URL that redirects to `http://127.0.0.1/` is the obvious
    way around a check that only looks at what was typed.
    """
    url = (url or "").strip()
    if not url:
        raise FetchError("Enter a URL.")
    if "://" not in url:
        url = "https://" + url
    if len(url) > 2000:
        raise FetchError("That URL is unreasonably long.")

    seen, chain = set(), []
    for _ in range(MAX_REDIRECTS + 1):
        if url in seen:
            raise FetchError("That URL redirects in a loop.")
        seen.add(url)
        status, headers, body, location = _request_once(url)
        chain.append({"url": url, "status": status})
        if status in (301, 302, 303, 307, 308) and location:
            from urllib.parse import urljoin

            url = urljoin(url, location)
            continue
        if status >= 400:
            raise FetchError(
                f"{urlparse(url).hostname} returned HTTP {status}. "
                + ("The page may be blocking automated requests — paste its HTML instead."
                   if status in (401, 403, 405, 429, 503) else "Check the address is right.")
            )
        if len(body) > MAX_BYTES:
            raise FetchError(f"That page is larger than {MAX_BYTES // (1024 * 1024)} MB.")

        content_type = headers.get("content-type", "")
        if content_type and not any(
            kind in content_type for kind in ("html", "xml", "text/plain")
        ):
            raise FetchError(f"That URL returned {content_type.split(';')[0]}, not a web page.")

        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
        try:
            html = body.decode(charset, errors="replace")
        except LookupError:
            html = body.decode("utf-8", errors="replace")
        return html, {
            "fetched_url": url,
            "status": status,
            "bytes": len(body),
            "content_type": content_type.split(";")[0] or None,
            "redirects": chain[:-1] or None,
        }
    raise FetchError(f"That URL redirected more than {MAX_REDIRECTS} times.")


def looks_like_url(value: str) -> bool:
    """Whether a single line of input is a URL rather than pasted markup."""
    text = (value or "").strip()
    if not text or "\n" in text or "<" in text:
        return False
    if text.lower().startswith(("http://", "https://")):
        return True
    # A bare domain: one token, a dot, a plausible TLD, and no spaces.
    return (" " not in text and "." in text
            and not text.endswith(".")
            and text.split(".")[-1].split("/")[0].isalpha()
            and len(text.split(".")[-1].split("/")[0]) >= 2)


def resolve_html(text: str, options: dict, *, key: str = "url") -> tuple[str, dict]:
    """Get page HTML from whichever the visitor supplied: a URL or the markup.

    Returns (html, source_meta). Raises FetchError with a message worth showing.
    """
    typed = (options.get(key) or "").strip() if isinstance(options, dict) else ""
    body = (text or "").strip()

    if typed:
        html, meta = fetch_page(typed)
        return html, {"source": "fetched", **meta}
    if body and looks_like_url(body):
        html, meta = fetch_page(body)
        return html, {"source": "fetched", **meta}
    if body:
        return body, {"source": "pasted HTML", "bytes": len(body)}
    raise FetchError("Enter the page's URL, or paste its HTML.")
