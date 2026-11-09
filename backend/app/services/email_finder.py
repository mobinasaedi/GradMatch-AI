"""Find *publicly published* emails on an official university page.

Rules (from the SRS):
- The page must be on the university's official domain(s) over HTTPS.
- Emails are only suggested; they are stored only after the user confirms them.
- The system never guesses an address from a name pattern.
"""

import html
import ipaddress
import re
import socket
import unicodedata
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

import httpx

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3


class EmailLookupError(ValueError):
    pass


def validate_official_url(url: str, domains: tuple[str, ...], resolver: Callable[[str], list[str]] | None = None) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise EmailLookupError("Please provide an https:// page URL.")
    host = parsed.hostname.lower()
    if not any(host == d or host.endswith("." + d) for d in domains):
        raise EmailLookupError(
            f"The page must be on the university's official domain ({', '.join(domains)})."
        )
    for ip in (resolver or _resolve)(host):
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise EmailLookupError("The page resolves to a non-public address.")
    return parsed.geturl()


def _resolve(host: str) -> list[str]:
    try:
        return list({info[4][0] for info in socket.getaddrinfo(host, 443)})
    except socket.gaierror as exc:
        raise EmailLookupError("The host could not be resolved.") from exc


def fetch_page(url: str, domains: tuple[str, ...], http: httpx.Client | None = None,
               resolver: Callable[[str], list[str]] | None = None) -> tuple[str, str]:
    """Fetch with manual redirect handling so every hop stays on the official domain."""
    client = http or httpx.Client(timeout=15, headers={"User-Agent": "GradMatchAI-student-tool/0.1"})
    current = validate_official_url(url, domains, resolver)
    for _ in range(MAX_REDIRECTS + 1):
        with client.stream("GET", current, follow_redirects=False) as resp:
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location")
                if not location:
                    raise EmailLookupError("Redirect without a location.")
                current = validate_official_url(urljoin(current, location), domains, resolver)
                continue
            if resp.status_code >= 400:
                raise EmailLookupError(f"The page returned HTTP {resp.status_code}.")
            body = b""
            for chunk in resp.iter_bytes():
                body += chunk
                if len(body) > MAX_BYTES:
                    break
            return current, body[:MAX_BYTES].decode(resp.encoding or "utf-8", errors="replace")
    raise EmailLookupError("Too many redirects.")


def _deobfuscate(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\s*[\[\(\{]\s*at\s*[\]\)\}]\s*", "@", text, flags=re.I)
    text = re.sub(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", ".", text, flags=re.I)
    return text


def _strip_tags(page: str) -> str:
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", page)))


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _name_tokens(full_name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"[\s\-]+", _ascii(full_name)) if p.isalpha()]
    if not parts:
        return "", ""
    return parts[0], parts[-1]


def extract_emails(page: str, professor_name: str) -> dict:
    text = _strip_tags(_deobfuscate(page))
    emails = set(EMAIL_RE.findall(text))
    for href in re.findall(r"""mailto:([^"'?>\s]+)""", _deobfuscate(page), flags=re.I):
        emails.update(EMAIL_RE.findall(href))
    first, last = _name_tokens(professor_name)
    mentions = bool(last) and last in _ascii(text)

    candidates = []
    for email in sorted(e.lower() for e in emails):
        local = _ascii(email.split("@")[0])
        matches = bool(last) and (last in local or (first[:1] + last) in local or (first + last) in local)
        candidates.append({"email": email, "local_part_matches_name": matches})
    suggested = next((c["email"] for c in candidates if c["local_part_matches_name"]), None) if mentions else None
    return {"candidates": candidates, "page_mentions_professor": mentions, "suggested_email": suggested}


def build_note(result: dict) -> str:
    if not result["candidates"]:
        return "No email address found on this page. Leave the email empty rather than guessing."
    if not result["page_mentions_professor"]:
        return "The page does not mention the professor's name, so it may be a general contact page. Verify manually."
    if result["suggested_email"]:
        return "Suggested address matches the professor's name. Confirm it on the page before saving."
    return "Emails were found but none clearly matches the professor's name. Verify manually."
