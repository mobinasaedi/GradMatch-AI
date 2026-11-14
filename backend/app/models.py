from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    auth_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    students: Mapped[list["Student"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    field: Mapped[str | None] = mapped_column(String(200), nullable=True)
    education: Mapped[str | None] = mapped_column(Text, nullable=True)
    gpa: Mapped[str | None] = mapped_column(String(50), nullable=True)
    interests: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    research_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    user: Mapped[User | None] = relationship(back_populates="students")


class Professor(Base):
    """A researcher found through OpenAlex.

    NOTE: OpenAlex does not say whether someone is faculty or accepts students.
    Everything here is *candidate* data that must be verified on the official page.
    """

    __tablename__ = "professors"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # OpenAlex short id, e.g. A123
    name: Mapped[str] = mapped_column(String(255))
    university_key: Mapped[str] = mapped_column(String(64), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    institution_name: Mapped[str] = mapped_column(String(255))
    works_count: Mapped[int] = mapped_column(Integer, default=0)
    cited_by_count: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    openalex_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # "openalex" (live API) or "demo-dataset" (seeded from data/raw for offline demos)
    data_source: Mapped[str] = mapped_column(String(24), default="openalex")

    # Email is only stored after the user confirms it from an official page.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    email_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    publications: Mapped[list["Publication"]] = relationship(
        back_populates="professor", cascade="all, delete-orphan"
    )


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (UniqueConstraint("work_id", "professor_id", name="uq_work_professor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_id: Mapped[str] = mapped_column(String(32), index=True)
    professor_id: Mapped[str] = mapped_column(ForeignKey("professors.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    professor: Mapped[Professor] = relationship(back_populates="publications")


class SearchCache(Base):
    """Caches which authors a (institution, query) search returned, to save API credits."""

    __tablename__ = "search_cache"

    key: Mapped[str] = mapped_column(String(500), primary_key=True)
    payload: Mapped[list] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InstitutionCache(Base):
    __tablename__ = "institution_cache"

    university_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    openalex_id: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(255))


class RecommendationRun(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    backend: Mapped[str] = mapped_column(String(32))
    alpha: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Recommendation.rank"
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("recommendation_runs.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    professor_id: Mapped[str] = mapped_column(ForeignKey("professors.id"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    semantic_score: Mapped[float] = mapped_column(Float)
    lexical_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)

    run: Mapped[RecommendationRun] = relationship(back_populates="recommendations")
    professor: Mapped[Professor] = relationship()


class Outreach(Base):
    """Manual email-tracking record for one (student, professor) pair."""

    __tablename__ = "outreach"
    __table_args__ = (UniqueConstraint("student_id", "professor_id", name="uq_outreach_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    professor_id: Mapped[str] = mapped_column(ForeignKey("professors.id"))
    status: Mapped[str] = mapped_column(String(32), default="not_started")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    professor: Mapped[Professor] = relationship()
    events: Mapped[list["OutreachEvent"]] = relationship(
        back_populates="outreach", cascade="all, delete-orphan", order_by="OutreachEvent.id"
    )


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outreach_id: Mapped[int] = mapped_column(ForeignKey("outreach.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    outreach: Mapped[Outreach] = relationship(back_populates="events")
