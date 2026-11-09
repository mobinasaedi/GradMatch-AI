"""Rule-based resume -> student profile extraction.

Deliberately simple and explainable: section detection + curated vocabularies.
The user can always edit the extracted profile before matching.
"""

import dataclasses
import re
from dataclasses import dataclass

from .taxonomy import SKILLS, TOPICS, count_term

SECTION_ALIASES = {
    "interests": ["research interests", "research interest", "interests", "areas of interest"],
    "skills": ["skills", "technical skills", "core skills", "technologies"],
    "education": ["education", "academic background"],
    "research": ["research experience", "research", "publications", "projects", "thesis"],
    "experience": ["experience", "work experience", "professional experience", "employment"],
}
_HEADING_TO_SECTION = {
    alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases
}
_HEADING_RE = re.compile(r"^\s*([A-Za-z][A-Za-z &/]{2,40}?)\s*:?\s*$")
_GPA_RE = re.compile(r"GPA[^0-9]{0,5}([0-9]+(?:\.[0-9]+)?)(?:\s*/\s*([0-9]+(?:\.[0-9]+)?))?", re.I)


@dataclass
class ExtractedProfile:
    name: str | None = None
    field: str | None = None
    education: str | None = None
    gpa: str | None = None
    interests: list[str] = dataclasses.field(default_factory=list)
    skills: list[str] = dataclasses.field(default_factory=list)
    research_experience: str | None = None


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "header"
    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m and m.group(1).strip().lower() in _HEADING_TO_SECTION:
            current = _HEADING_TO_SECTION[m.group(1).strip().lower()]
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _guess_name(text: str) -> str | None:
    for line in [ln.strip() for ln in text.splitlines() if ln.strip()][:5]:
        if "@" in line or any(ch.isdigit() for ch in line):
            continue
        if line.lower() in _HEADING_TO_SECTION or line.lower() in {"resume", "curriculum vitae", "cv"}:
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and len(line) <= 40:
            return line
    return None


def _guess_field(text: str) -> str | None:
    lowered = text.lower()
    for needle, label in [
        ("computer engineering", "Computer Engineering"),
        ("computer science", "Computer Science"),
        ("artificial intelligence", "Artificial Intelligence"),
        ("data science", "Data Science"),
        ("software engineering", "Software Engineering"),
        ("electrical engineering", "Electrical Engineering"),
    ]:
        if needle in lowered:
            return label
    return None


def _clean_items(block: str) -> list[str]:
    items = re.split(r"[,;\n•·•|]+", block)
    cleaned = []
    for item in items:
        item = item.strip(" -–—*\t.")
        if 2 <= len(item) <= 60:
            cleaned.append(item)
    return cleaned


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def extract_topics(text: str, interests_block: str = "") -> list[str]:
    scores: dict[str, int] = {}
    for topic, aliases in TOPICS.items():
        score = sum(count_term(text, a) for a in aliases + [topic])
        score += 5 * sum(count_term(interests_block, a) for a in aliases + [topic]) if interests_block else 0
        if score:
            scores[topic] = score
    return [t for t, _ in sorted(scores.items(), key=lambda kv: -kv[1])]


def extract_skills(text: str) -> list[str]:
    found = [(s, count_term(text, s)) for s in SKILLS]
    return [s for s, c in sorted(found, key=lambda kv: -kv[1]) if c]


def extract_profile(text: str) -> ExtractedProfile:
    sections = split_sections(text)
    interests_block = sections.get("interests", "")

    explicit = _clean_items(interests_block)[:8]
    topics = extract_topics(text, interests_block)[:8]
    interests = _dedupe(explicit + topics)[:10]

    skills_block = sections.get("skills", "")
    skills = extract_skills(text)
    for item in _clean_items(skills_block)[:15]:
        if len(item.split()) <= 3:
            skills.append(item)

    gpa = None
    if m := _GPA_RE.search(text):
        gpa = f"{m.group(1)}/{m.group(2)}" if m.group(2) else m.group(1)

    research = sections.get("research") or sections.get("experience") or ""
    education = sections.get("education") or None

    return ExtractedProfile(
        name=_guess_name(text),
        field=_guess_field(text),
        education=education[:600] if education else None,
        gpa=gpa,
        interests=interests,
        skills=_dedupe(skills)[:20],
        research_experience=research[:1500] or None,
    )
