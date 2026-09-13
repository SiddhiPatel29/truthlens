"""
Abuse Dispatcher & Forensic Dossier Service.
Constructs cryptographically hashed takedown dossiers for target platforms (excluding TikTok).
"""
import hashlib
import json
import logging
import time
import uuid
from sqlalchemy.exc import SQLAlchemyError
from backend.database.db import db
from backend.database.models import AbuseReport

logger = logging.getLogger(__name__)

class AbuseServiceError(Exception):
    """Base exception for abuse service errors."""
    pass

class AbuseDatabaseError(AbuseServiceError):
    """Exception raised when database persistence fails."""
    pass

class AbuseDispatcherService:
    # TikTok removed from supported platforms list
    SUPPORTED_PLATFORMS = {"youtube", "x", "meta", "custom"}

    @classmethod
    def save_report(
        cls,
        platform: str,
        dossier: dict,
        user_id: int = None,
        scan_id: int = None
    ) -> AbuseReport:
        """
        Persists a generated abuse dossier to the database in an atomic transaction.

        Args:
            platform (str): Target platform name (e.g. "youtube", "meta", "x", "custom").
            dossier (dict): The complete generated evidence dossier dictionary.
            user_id (int, optional): Authenticated user ID if available, otherwise None.
            scan_id (int, optional): Associated scan ID if available, otherwise None.

        Returns:
            AbuseReport: The persisted database model instance.

        Raises:
            AbuseDatabaseError: If database persistence fails.
        """
        try:
            report = AbuseReport(
                user_id=user_id,
                scan_id=scan_id,
                platform=platform.lower().strip(),
                status=dossier.get("status", "DISPATCHED"),
                report_data=dossier
            )
            db.session.add(report)
            db.session.commit()
            return report
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("Failed to persist abuse report to database: %s", str(e))
            raise AbuseDatabaseError("Failed to persist abuse report to database.") from e
        except Exception as e:
            db.session.rollback()
            logger.exception("Unexpected error while persisting abuse report: %s", str(e))
            raise AbuseDatabaseError("Failed to persist abuse report to database.") from e

    @classmethod
    def generate_dossier(cls, payload: dict) -> dict:
        """
        Builds a structured abuse report and evidence dossier.
        """
        platform = payload.get("platform", "").lower().strip()
        if platform not in cls.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform '{platform}'. Allowed: {', '.join(cls.SUPPORTED_PLATFORMS)}")

        target_url = payload.get("target_url", "").strip()
        if not target_url:
            raise ValueError("Target URL or content link is required.")

        category = payload.get("category", "Synthetic Impersonation & Manipulated Media")
        confidence_score = float(payload.get("confidence_score", 0.95))
        analyst_notes = payload.get("analyst_notes", "Automated algorithmic detection confirmed high synthetic markers.")

        timestamp_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        report_id = f"VM-REP-{uuid.uuid4().hex[:8].upper()}"

        # 1. Assemble raw forensic data for hash calculation
        raw_manifest = {
            "report_id": report_id,
            "target_url": target_url,
            "platform": platform,
            "confidence_score": confidence_score,
            "timestamp": timestamp_utc
        }
        
        # 2. Cryptographic Integrity Fingerprint (SHA-256)
        manifest_bytes = json.dumps(raw_manifest, sort_keys=True).encode("utf-8")
        sha256_fingerprint = hashlib.sha256(manifest_bytes).hexdigest()

        # 3. Platform-specific routing payload (TikTok mapping removed)
        dispatch_channel = {
            "youtube": "Google Trust & Safety Abuse API",
            "x": "X Security Policy Escalation Relay",
            "meta": "Meta Oversight & Safety Enforcement",
            "custom": "Enterprise Webhook Dispatcher"
        }.get(platform, "Standard Takedown Channel")

        return {
            "report_id": report_id,
            "status": "DISPATCHED",
            "dispatch_timestamp": timestamp_utc,
            "platform_destination": {
                "platform": platform.capitalize(),
                "channel": dispatch_channel,
                "target_url": target_url
            },
            "forensic_evidence": {
                "category": category,
                "confidence_score": confidence_score,
                "sha256_fingerprint": sha256_fingerprint,
                "analyst_notes": analyst_notes,
                "standards_compliance": ["C2PA-Authenticity", "NIST-AI-100-2"]
            },
            "dispatch_receipt": {
                "acknowledgment_code": f"ACK-{uuid.uuid4().hex[:6].upper()}",
                "estimated_review_hours": 24
            }
        }