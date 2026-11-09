from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OutreachStatus(str, Enum):
    not_started = "not_started"
    draft_ready = "draft_ready"
    sent = "sent"
    replied = "replied"
    follow_up_needed = "follow_up_needed"
    closed = "closed"


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    name: str | None = None
    field: str | None = None
    education: str | None = None
    gpa: str | None = None
    interests: list[str] = []
    skills: list[str] = []
    research_experience: str | None = None
    created_at: datetime


class StudentUpdate(BaseModel):
    name: str | None = None
    field: str | None = None
    education: str | None = None
    gpa: str | None = None
    interests: list[str] | None = None
    skills: list[str] | None = None
    research_experience: str | None = None


class UniversityOut(BaseModel):
    key: str
    name: str
    country_code: str
    country: str
    website: str


class RecommendRequest(BaseModel):
    countries: list[str] = Field(min_length=1, description="ISO country codes, e.g. ['CA','DE']")
    university_keys: list[str] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=20)


class ProfessorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    university_key: str
    institution_name: str
    country_code: str
    works_count: int
    cited_by_count: int
    topics: list[str] = []
    openalex_url: str | None = None
    email: str | None = None
    email_source_url: str | None = None


class EvidencePaper(BaseModel):
    title: str
    year: int | None = None
    doi: str | None = None
    similarity: float


class ExplanationOut(BaseModel):
    summary: str = ""
    matched_topics: list[str] = []
    shared_terms: list[str] = []
    evidence_papers: list[EvidencePaper] = []


class RecommendationOut(BaseModel):
    rank: int
    score: float
    semantic_score: float
    lexical_score: float
    professor: ProfessorOut
    explanation: ExplanationOut
    outreach_id: int | None = None
    outreach_status: OutreachStatus | None = None


class RecommendationRunOut(BaseModel):
    run_id: int
    student_id: int
    backend: str
    created_at: datetime
    params: dict
    warnings: list[str] = []
    results: list[RecommendationOut]


class EmailLookupRequest(BaseModel):
    page_url: str = Field(description="Official faculty/lab page of the professor (https).")


class EmailCandidate(BaseModel):
    email: str
    local_part_matches_name: bool


class EmailLookupOut(BaseModel):
    source_url: str
    page_mentions_professor: bool
    candidates: list[EmailCandidate]
    suggested_email: str | None = None
    note: str


class EmailConfirm(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    source_url: str


class OutreachOut(BaseModel):
    id: int
    student_id: int
    professor: ProfessorOut
    status: OutreachStatus
    notes: str | None = None
    updated_at: datetime


class OutreachUpdate(BaseModel):
    status: OutreachStatus | None = None
    notes: str | None = None


class OutreachEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    note: str | None = None
    created_at: datetime


class OutreachStats(BaseModel):
    total: int
    by_status: dict[str, int]


class DraftOut(BaseModel):
    subject: str
    body: str
    note: str = "Template draft, not AI-generated. Review and edit before sending from your own mail client."


from pydantic import EmailStr, field_validator

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)

class AuthUserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
