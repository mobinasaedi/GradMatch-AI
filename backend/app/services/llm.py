"""Optional AI email drafting through any OpenAI-compatible chat-completions endpoint.

The template draft in ``draft.py`` always works. When ``LLM_API_KEY`` is set, this module
rewrites that template into a shorter, more specific email using the same evidence that
produced the match. Nothing is ever sent automatically: the user copies the text from the
app into their own mail client.
"""

from __future__ import annotations

import httpx

from ..config import get_settings

SYSTEM_PROMPT = (
    "You write cold emails from a Master's applicant to a university professor. "
    "Be specific, factual, and short (120-170 words). Never invent achievements, papers, "
    "or numbers that are not in the provided facts. Use the professor's real paper title if "
    "one is given. No emojis, no flattery, no generic phrases like 'I hope this finds you well'. "
    "Return JSON with exactly two keys: subject and body."
)


class LLMError(RuntimeError):
    pass


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.llm_api_key)


def _facts(
    student_name: str | None,
    field: str | None,
    professor_name: str,
    institution: str | None,
    explanation: dict | None,
) -> str:
    explanation = explanation or {}
    topics = explanation.get("matched_topics") or []
    papers = explanation.get("evidence_papers") or []
    terms = explanation.get("shared_terms") or []
    lines = [
        f"Student name: {student_name or '[your name]'}",
        f"Student field: {field or 'not specified'}",
        f"Professor: {professor_name}" + (f" ({institution})" if institution else ""),
        f"Shared research topics: {', '.join(topics) if topics else 'n/a'}",
        f"Overlapping technical terms: {', '.join(terms[:6]) if terms else 'n/a'}",
    ]
    if papers:
        paper = papers[0]
        year = f" ({paper['year']})" if paper.get("year") else ""
        lines.append(f"Most relevant paper: \"{paper['title']}\"{year}")
    return "\n".join(lines)


def draft_email(
    *,
    student_name: str | None,
    field: str | None,
    professor_name: str,
    institution: str | None,
    explanation: dict | None,
    template_subject: str,
    template_body: str,
) -> tuple[str, str]:
    """Return (subject, body). Raises LLMError when the call fails."""
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not configured.")

    payload = {
        "model": settings.llm_model,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Facts:\n"
                    f"{_facts(student_name, field, professor_name, institution, explanation)}\n\n"
                    "Starting draft (improve it, keep the structure):\n"
                    f"Subject: {template_subject}\n\n{template_body}"
                ),
            },
        ],
    }
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach the LLM endpoint: {exc}") from exc

    if response.status_code >= 400:
        raise LLMError(f"LLM endpoint returned HTTP {response.status_code}: {response.text[:200]}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError("Unexpected response shape from the LLM endpoint.") from exc

    import json

    try:
        data = json.loads(content)
        subject = str(data.get("subject") or template_subject).strip()
        body = str(data.get("body") or "").strip()
    except ValueError:
        subject, body = template_subject, content.strip()

    if not body:
        raise LLMError("The LLM returned an empty email body.")
    return subject, body
