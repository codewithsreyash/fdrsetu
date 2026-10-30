from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Numeric, Boolean, ForeignKey,
    Text, Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


class Role(str, enum.Enum):
    institution = "institution"
    officer = "officer"          # AICTE officer
    bank = "bank"                # bank officer
    admin = "admin"              # super administrator


class FDRStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    verified = "verified"
    expired = "expired"
    renewed = "renewed"
    released = "released"


class RiskLevel(str, enum.Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    verified = "verified"
    rejected = "rejected"


class ReleaseStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(Role), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="users")
    bank = relationship("Bank", back_populates="users")


class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    institution_type = Column(String(64), default="Engineering College")
    state = Column(String(64))
    city = Column(String(64))
    contact_email = Column(String(255))
    contact_phone = Column(String(32))
    is_demo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="institution")
    fdrs = relationship("FDRRecord", back_populates="institution")


class Bank(Base):
    __tablename__ = "banks"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    short_code = Column(String(16), unique=True, nullable=False)
    is_demo = Column(Boolean, default=True)

    users = relationship("User", back_populates="bank")
    fdrs = relationship("FDRRecord", back_populates="bank")


class FDRRecord(Base):
    __tablename__ = "fdr_records"
    id = Column(Integer, primary_key=True)
    fdr_uid = Column(String(32), unique=True, nullable=False, index=True)  # FDRSETU-XXXXXX
    fdr_number = Column(String(64), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    branch = Column(String(255))
    ifsc = Column(String(16))
    amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=True)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    status = Column(SAEnum(FDRStatus), default=FDRStatus.pending, nullable=False)
    verification_status = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.none, nullable=False)
    renewed_from_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=True)
    is_demo = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="fdrs")
    bank = relationship("Bank", back_populates="fdrs")
    documents = relationship("FDRDocument", back_populates="fdr", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="fdr", cascade="all, delete-orphan")


class FDRDocument(Base):
    __tablename__ = "fdr_documents"
    id = Column(Integer, primary_key=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(512), nullable=False)
    content_type = Column(String(64))
    extracted_data = Column(Text)          # JSON string of OCR result
    extraction_status = Column(String(32), default="pending")  # pending/done/failed/mock
    created_at = Column(DateTime, default=datetime.utcnow)

    fdr = relationship("FDRRecord", back_populates="documents")


class MockBankLedger(Base):
    """Simulated bank-side records used by the mock verification API."""
    __tablename__ = "mock_bank_ledger"
    id = Column(Integer, primary_key=True)
    fdr_number = Column(String(64), nullable=False, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False)
    branch = Column(String(255))
    ifsc = Column(String(16))
    amount = Column(Numeric(15, 2))
    issue_date = Column(Date)
    maturity_date = Column(Date)

    bank = relationship("Bank")


class VerificationRequest(Base):
    __tablename__ = "verification_requests"
    id = Column(Integer, primary_key=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.id"))
    assigned_bank_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    fdr = relationship("FDRRecord")


class VerificationHistory(Base):
    __tablename__ = "verification_history"
    id = Column(Integer, primary_key=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=False)
    verification_request_id = Column(Integer, ForeignKey("verification_requests.id"), nullable=True)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    bank_confirmed_number = Column(Boolean)
    bank_confirmed_amount = Column(Boolean)
    bank_confirmed_maturity = Column(Boolean)
    bank_confirmed_branch = Column(Boolean)
    result = Column(String(32))            # verified / mismatch / rejected
    remarks = Column(Text)
    mock_api = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    fdr = relationship("FDRRecord")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    id = Column(Integer, primary_key=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=False)
    alert_type = Column(String(64), nullable=False)   # duplicate_fdr / amount_mismatch / ...
    severity = Column(SAEnum(RiskLevel), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(32), default="open")       # open / reviewed / dismissed
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    fdr = relationship("FDRRecord", back_populates="risk_alerts")


class RenewalRecord(Base):
    __tablename__ = "renewal_records"
    id = Column(Integer, primary_key=True)
    old_fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=False)
    new_fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    status = Column(String(32), default="pending")   # pending / submitted / completed
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReleaseRequest(Base):
    __tablename__ = "release_requests"
    id = Column(Integer, primary_key=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    reason = Column(Text)
    status = Column(SAEnum(ReleaseStatus), default=ReleaseStatus.pending)
    supporting_doc_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fdr = relationship("FDRRecord")


class ApprovalHistory(Base):
    __tablename__ = "approval_history"
    id = Column(Integer, primary_key=True)
    release_request_id = Column(Integer, ForeignKey("release_requests.id"), nullable=False)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(32), nullable=False)      # reviewed / approved / rejected / observation
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)      # null = broadcast to role
    role = Column(String(32), nullable=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    kind = Column(String(32), default="info")        # maturity / risk / verification / release
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("kind", "message", "role", "institution_id",
                                       name="uq_notification_dedup"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_email = Column(String(255))
    action = Column(String(64), nullable=False)
    entity = Column(String(64))
    entity_id = Column(Integer)
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
