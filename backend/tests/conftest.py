import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.auth import get_current_user
from app.models import User
from app.deps import get_embedder, get_openalex_client
from app.main import create_app
from app.services.matcher import TfidfEmbedder

INSTITUTION = "I100"


def _authorship(author_id: str, name: str, position: str = "last") -> dict:
    return {
        "author_position": position,
        "author": {"id": f"https://openalex.org/{author_id}", "display_name": name},
        "institutions": [{"id": f"https://openalex.org/{INSTITUTION}", "lineage": [f"https://openalex.org/{INSTITUTION}"]}],
    }


def _work(wid: str, title: str, abstract_words: str, year: int, authorships: list[dict]) -> dict:
    return {
        "id": f"https://openalex.org/{wid}",
        "title": title,
        "publication_year": year,
        "doi": f"https://doi.org/10.1000/{wid}",
        "authorships": authorships,
        "abstract_inverted_index": {w: [i] for i, w in enumerate(abstract_words.split())},
        "keywords": [],
    }


class FakeOpenAlex:
    """Deterministic stand-in for the OpenAlex client (no network)."""

    def __init__(self):
        a1, a2, a3 = (
            _authorship("A1", "Ada Nlp", "last"),
            _authorship("A2", "Carl Vision", "last"),
            _authorship("A3", "Junior Student", "first"),
        )
        self.works = [
            _work("W1", "Large language models for question answering", "we study large language models and natural language processing for question answering", 2024, [a1]),
            _work("W2", "Robust NLP with transformers", "natural language processing robustness of transformer language models", 2023, [a1, a3]),
            _work("W3", "Object detection in street scenes", "convolutional networks for object detection and image segmentation in computer vision", 2024, [a2]),
        ]
        self.authors = [
            {"id": "https://openalex.org/A1", "display_name": "Ada Nlp", "works_count": 80, "cited_by_count": 3000,
             "last_known_institutions": [{"id": f"https://openalex.org/{INSTITUTION}"}],
             "topics": [{"display_name": "Natural Language Processing"}, {"display_name": "Large Language Models"}]},
            {"id": "https://openalex.org/A2", "display_name": "Carl Vision", "works_count": 60, "cited_by_count": 2000,
             "last_known_institutions": [{"id": f"https://openalex.org/{INSTITUTION}"}],
             "topics": [{"display_name": "Computer Vision"}]},
            {"id": "https://openalex.org/A3", "display_name": "Junior Student", "works_count": 2, "cited_by_count": 3,
             "last_known_institutions": [{"id": f"https://openalex.org/{INSTITUTION}"}], "topics": []},
        ]
        self.calls: list[str] = []

    def find_institution(self, name, country_code):
        self.calls.append("find_institution")
        return {"id": f"https://openalex.org/{INSTITUTION}", "display_name": name}

    def search_works(self, institution_id, query, from_year, per_page=100):
        self.calls.append("search_works")
        return self.works

    def get_authors(self, ids):
        self.calls.append("get_authors")
        return [a for a in self.authors if a["id"].rsplit("/", 1)[-1] in ids]

    def recent_works_by_authors(self, ids, from_year, batch=15):
        self.calls.append("recent_works")
        return self.works


@pytest.fixture()
def fake_openalex():
    return FakeOpenAlex()


@pytest.fixture()
def client(fake_openalex):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    test_user = User(id=1, email="test@example.com", password_hash="test-hash")
    with Session() as db:
        db.add(test_user)
        db.commit()
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_openalex_client] = lambda: fake_openalex
    app.dependency_overrides[get_embedder] = lambda: TfidfEmbedder()
    with TestClient(app) as c:  # runs lifespan (init_db on the default engine is harmless: sqlite://)
        yield c


SAMPLE_RESUME = """Sara Ahmadi
sara@example.com

Education
BSc in Computer Engineering, Example University. GPA: 18.2/20

Research Interests
Natural Language Processing, Large Language Models, Robustness

Skills
Python, PyTorch, Hugging Face, Docker, Git

Research Experience
Bachelor thesis on adversarial robustness of large language models for question answering.
Built transformer-based text classification pipelines in PyTorch.
"""


@pytest.fixture()
def sample_resume() -> str:
    return SAMPLE_RESUME
