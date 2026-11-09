"""Deterministic email draft template (no LLM in the MVP)."""


def last_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[-1] if parts else full_name


def build_draft(student_name: str | None, field: str | None, professor_name: str,
                explanation: dict | None) -> tuple[str, str]:
    explanation = explanation or {}
    topics = explanation.get("matched_topics") or []
    papers = explanation.get("evidence_papers") or []
    topic = topics[0] if topics else "your research area"
    sender = student_name or "[Your name]"
    background = f" with a background in {field}" if field else ""

    paper_line = ""
    if papers:
        paper_line = (
            f"I recently read your paper \"{papers[0]['title']}\" and found it closely related "
            f"to my own interests.\n\n"
        )

    subject = f"Prospective Master's student interested in {topic}"
    body = (
        f"Dear Professor {last_name(professor_name)},\n\n"
        f"My name is {sender}, and I am applying for Master's programs{background}. "
        f"I am writing because my research interests in {topic} align with your recent work.\n\n"
        f"{paper_line}"
        "[Add 2-3 sentences about your most relevant project or research experience.]\n\n"
        "Could you let me know whether you expect to supervise Master's students in the coming "
        "academic year? I have attached my CV and would be happy to share more details.\n\n"
        "Thank you for your time and consideration.\n\n"
        f"Best regards,\n{sender}\n"
    )
    return subject, body
