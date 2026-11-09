import httpx
import pytest

from app.services.email_finder import (
    EmailLookupError,
    build_note,
    extract_emails,
    fetch_page,
    validate_official_url,
)

DOMAINS = ("utoronto.ca",)
PUBLIC = lambda host: ["93.184.216.34"]  # noqa: E731


def test_url_validation():
    assert validate_official_url("https://www.cs.utoronto.ca/~ada", DOMAINS, PUBLIC)
    for bad in [
        "http://www.cs.utoronto.ca/~ada",          # not https
        "https://evil.com/utoronto.ca",             # wrong host
        "https://utoronto.ca.evil.com/",            # suffix trick
        "https://user:pw@www.utoronto.ca/",         # credentials
    ]:
        with pytest.raises(EmailLookupError):
            validate_official_url(bad, DOMAINS, PUBLIC)


def test_private_addresses_are_blocked():
    with pytest.raises(EmailLookupError):
        validate_official_url("https://www.utoronto.ca/", DOMAINS, lambda h: ["127.0.0.1"])


def test_extracts_and_deobfuscates_emails():
    page = """<html><body><h1>Prof. Ada Nlp</h1>
    <a href="mailto:ada.nlp@cs.utoronto.ca">email</a>
    <p>Office: ada [dot] second [at] cs.utoronto.ca</p>
    <p>Admin: office@cs.utoronto.ca</p></body></html>"""
    r = extract_emails(page, "Ada Nlp")
    emails = {c["email"] for c in r["candidates"]}
    assert {"ada.nlp@cs.utoronto.ca", "office@cs.utoronto.ca"} <= emails
    assert r["page_mentions_professor"] is True
    assert r["suggested_email"] in {"ada.nlp@cs.utoronto.ca", "ada.second@cs.utoronto.ca"}
    assert "office@cs.utoronto.ca" != r["suggested_email"]


def test_general_page_gives_no_suggestion():
    r = extract_emails("<p>Contact the department: info@cs.utoronto.ca</p>", "Ada Nlp")
    assert r["page_mentions_professor"] is False
    assert r["suggested_email"] is None
    assert "does not mention" in build_note(r)


def test_no_email_never_guesses():
    r = extract_emails("<p>Ada Nlp works on NLP.</p>", "Ada Nlp")
    assert r["candidates"] == [] and r["suggested_email"] is None
    assert "guessing" in build_note(r)


def test_redirect_off_domain_is_blocked():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.com/"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(EmailLookupError):
        fetch_page("https://www.utoronto.ca/x", DOMAINS, http, PUBLIC)


def test_fetch_page_returns_body():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="<p>hi ada@utoronto.ca</p>")))
    url, body = fetch_page("https://www.utoronto.ca/x", DOMAINS, http, PUBLIC)
    assert url == "https://www.utoronto.ca/x" and "ada@utoronto.ca" in body
