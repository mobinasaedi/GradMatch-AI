import httpx
import pytest

from app.services.openalex import OpenAlexClient, OpenAlexError, reconstruct_abstract, short_id


def make_client(handler, **kw):
    return OpenAlexClient(
        api_key=kw.pop("api_key", "KEY"),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda s: None,
        **kw,
    )


def test_abstract_reconstruction_and_short_id():
    assert reconstruct_abstract({"hello": [0], "world": [1], "again": [2]}) == "hello world again"
    assert reconstruct_abstract(None) is None
    assert short_id("https://openalex.org/A123") == "A123"
    assert short_id(None) is None


def test_api_key_is_sent_and_results_returned():
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"results": [{"id": "https://openalex.org/I1", "display_name": "X"}]})

    c = make_client(handler)
    assert c.institution_candidates("X", "CA")[0]["display_name"] == "X"
    assert seen["api_key"] == "KEY" and seen["filter"] == "country_code:CA"


def test_retries_on_429_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"results": []})

    assert make_client(handler).get_authors(["A1"]) == []
    assert calls["n"] == 3


def test_gives_up_after_max_retries():
    c = make_client(lambda r: httpx.Response(503), max_retries=2)
    with pytest.raises(OpenAlexError):
        c.get_authors(["A1"])


def test_missing_key_error_is_actionable():
    c = make_client(lambda r: httpx.Response(409), api_key=None)
    with pytest.raises(OpenAlexError, match="OPENALEX_API_KEY"):
        c.get_authors(["A1"])


def test_author_batches_use_pipe_filter():
    filters = []

    def handler(request):
        filters.append(request.url.params["filter"])
        return httpx.Response(200, json={"results": []})

    make_client(handler).get_authors([f"A{i}" for i in range(120)])
    assert len(filters) == 3  # 50 + 50 + 20
    assert filters[0].startswith("openalex:A0|A1|")
