from app.services.profile_extractor import extract_profile, split_sections


def test_sections_are_detected(sample_resume):
    sections = split_sections(sample_resume)
    assert "Natural Language Processing" in sections["interests"]
    assert "Python" in sections["skills"]


def test_profile_fields(sample_resume):
    p = extract_profile(sample_resume)
    assert p.name == "Sara Ahmadi"
    assert p.field == "Computer Engineering"
    assert p.gpa == "18.2/20"
    assert "Natural Language Processing" in p.interests
    assert "Large Language Models" in p.interests
    assert {"Python", "PyTorch", "Docker"} <= set(p.skills)
    assert p.research_experience and "adversarial" in p.research_experience


def test_interests_are_deduplicated_case_insensitively(sample_resume):
    p = extract_profile(sample_resume)
    lowered = [i.lower() for i in p.interests]
    assert len(lowered) == len(set(lowered))


def test_resume_without_sections_still_yields_topics():
    text = "Jane Doe\nI work on reinforcement learning and computer vision projects in Python. " * 3
    p = extract_profile(text)
    assert "Reinforcement Learning" in p.interests
    assert "Computer Vision" in p.interests
