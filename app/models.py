"""SQLAlchemy ORM models (TH-005)."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class ApiKey(Base):
    __tablename__ = "api_keys"
    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CheckRecord(Base):
    __tablename__ = "checks"
    check_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    org: Mapped[str] = mapped_column(String(160), default="", index=True)
    payload: Mapped[str] = mapped_column(Text)            # JSON of the VerifyResponse
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NetworkReport(Base):
    __tablename__ = "network_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    combo_hash: Mapped[str] = mapped_column(String(64), index=True)
    org: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("combo_hash", "org", name="uq_report_combo_org"),)


class NetworkIdentity(Base):
    __tablename__ = "network_identities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_hash: Mapped[str] = mapped_column(String(64), index=True)     # hash(phone) or hash(email)
    name_hash: Mapped[str] = mapped_column(String(64))               # hash(name) — no raw PII
    __table_args__ = (UniqueConstraint("id_hash", "name_hash", name="uq_identity_hash_name"),)


class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    org: Mapped[str] = mapped_column(String(160), primary_key=True)
    plan: Mapped[str] = mapped_column(String(40), default="free")
    balance: Mapped[float] = mapped_column(Float, default=0.0)


class Contribution(Base):
    __tablename__ = "contributions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org: Mapped[str] = mapped_column(String(160), index=True)
    outcome: Mapped[str] = mapped_column(String(40))
    credits: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Dispute(Base):
    __tablename__ = "disputes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    check_id: Mapped[str] = mapped_column(String(48), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")   # open|reinvestigated|resolved
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
