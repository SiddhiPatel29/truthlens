"""
Database Models for VeraMedia AI Backend.
Defines User, Scan, ScanResult, and AbuseReport models and their relationships.
"""
from datetime import datetime, timezone
from sqlalchemy import func
from backend.database.db import db

def utc_now():
    """Returns current UTC datetime."""
    return datetime.now(timezone.utc)

class User(db.Model):
    """Represents a platform user account."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    # User → many Scans
    scans = db.relationship(
        "Scan",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # User → many AbuseReports
    abuse_reports = db.relationship(
        "AbuseReport",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}'>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Scan(db.Model):
    """Represents a submitted forensic analysis scan."""
    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # user_id is nullable in Phase 2 because authentication is deferred to Phase 3
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    media_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default="PENDING", nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User", back_populates="scans")

    # Scan → one ScanResult (uselist=False)
    result = db.relationship(
        "ScanResult",
        back_populates="scan",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Scan → many AbuseReports
    abuse_reports = db.relationship(
        "AbuseReport",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<Scan id={self.id} media_type='{self.media_type}' status='{self.status}'>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "media_type": self.media_type,
            "filename": self.filename,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ScanResult(db.Model):
    """Represents the forensic outcome of a completed Scan."""
    __tablename__ = "scan_results"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    prediction = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    risk_level = db.Column(db.String(50), nullable=False)
    result_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Relationships
    scan = db.relationship("Scan", back_populates="result")

    def __repr__(self):
        return f"<ScanResult id={self.id} scan_id={self.scan_id} prediction='{self.prediction}'>"

    def to_dict(self):
        return {
            "id": self.id,
            "scan_id": self.scan_id,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "result_data": self.result_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AbuseReport(db.Model):
    """Represents an evidence dossier generated for takedown dispatch."""
    __tablename__ = "abuse_reports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True)
    platform = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="DISPATCHED", nullable=False)
    report_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="abuse_reports")
    scan = db.relationship("Scan", back_populates="abuse_reports")

    def __repr__(self):
        return f"<AbuseReport id={self.id} platform='{self.platform}' status='{self.status}'>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "scan_id": self.scan_id,
            "platform": self.platform,
            "status": self.status,
            "report_data": self.report_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
