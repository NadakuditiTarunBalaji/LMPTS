"""
prior_learning_request.py
--------------------------
Represents a learner's request for prior learning recognition.

Workflow:
    Learner submits (PENDING)
         ↓
    Instructor reviews → INSTRUCTOR_REVIEWED
         ↓
    Admin decides → APPROVED / REJECTED / INFO_REQUESTED
"""

from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass


class PLRStatus:
    PENDING              = "PENDING"
    INSTRUCTOR_REVIEWED  = "INSTRUCTOR_REVIEWED"
    APPROVED             = "APPROVED"
    REJECTED             = "REJECTED"
    INFO_REQUESTED       = "INFO_REQUESTED"


class PLRPathway:
    TRANSFER    = "TRANSFER"
    ASSESSMENT  = "ASSESSMENT"
    EXEMPTION   = "EXEMPTION"


class PriorLearningRequest:
    """
    A learner's request to have external learning recognized.

    Attributes:
        id                        : Database primary key
        learner_id                : FK to learners
        course_code               : Course to be credited
        pathway                   : TRANSFER / ASSESSMENT / EXEMPTION
        evidence_description      : Learner's description of evidence
        external_platform         : Where they completed the course
        external_score            : Score achieved externally
        status                    : Current workflow status
        instructor_recommendation : APPROVE / REJECT / INFO_REQUESTED
        instructor_note           : Instructor's comments
        instructor_id             : Instructor who reviewed
        admin_note                : Admin's decision comments
        admin_id                  : Admin who made final decision
        submitted_at              : When request was submitted
        reviewed_by_instructor_at : When instructor reviewed
        decided_by_admin_at       : When admin decided
    """

    def __init__(
        self,
        learner_id:           int,
        course_code:          str,
        pathway:              str,
        evidence_description: str,
        external_platform:    str  = "",
        external_score:       Optional[float] = None,
        status:               str  = PLRStatus.PENDING,
        instructor_recommendation: Optional[str] = None,
        instructor_note:      Optional[str] = None,
        instructor_id:        Optional[int] = None,
        admin_note:           Optional[str] = None,
        admin_id:             Optional[int] = None,
        id:                   Optional[int] = None,
        submitted_at:         Optional[datetime] = None,
        reviewed_by_instructor_at: Optional[datetime] = None,
        decided_by_admin_at:  Optional[datetime] = None,
    ):
        self.id                         = id
        self.learner_id                 = learner_id
        self.course_code                = course_code
        self.pathway                    = pathway
        self.evidence_description       = evidence_description
        self.external_platform          = external_platform
        self.external_score             = external_score
        self.status                     = status
        self.instructor_recommendation  = instructor_recommendation
        self.instructor_note            = instructor_note
        self.instructor_id              = instructor_id
        self.admin_note                 = admin_note
        self.admin_id                   = admin_id
        self.submitted_at               = submitted_at or datetime.now(timezone.utc)
        self.reviewed_by_instructor_at  = reviewed_by_instructor_at
        self.decided_by_admin_at        = decided_by_admin_at

    def to_dict(self) -> dict:
        def fmt(dt): return dt.isoformat() if dt else None
        return {
            "id":                         self.id,
            "learner_id":                 self.learner_id,
            "course_code":                self.course_code,
            "pathway":                    self.pathway,
            "evidence_description":       self.evidence_description,
            "external_platform":          self.external_platform,
            "external_score":             self.external_score,
            "status":                     self.status,
            "instructor_recommendation":  self.instructor_recommendation,
            "instructor_note":            self.instructor_note,
            "instructor_id":              self.instructor_id,
            "admin_note":                 self.admin_note,
            "admin_id":                   self.admin_id,
            "submitted_at":               fmt(self.submitted_at),
            "reviewed_by_instructor_at":  fmt(self.reviewed_by_instructor_at),
            "decided_by_admin_at":        fmt(self.decided_by_admin_at),
        }

    @classmethod
    def from_dict(cls, row: dict) -> "PriorLearningRequest":
        def parse_dt(v):
            if isinstance(v, str): return datetime.fromisoformat(v)
            return v
        return cls(
            id                        = row.get("id"),
            learner_id                = row["learner_id"],
            course_code               = row["course_code"],
            pathway                   = row["pathway"],
            evidence_description      = row["evidence_description"],
            external_platform         = row.get("external_platform", ""),
            external_score            = row.get("external_score"),
            status                    = row.get("status", PLRStatus.PENDING),
            instructor_recommendation = row.get("instructor_recommendation"),
            instructor_note           = row.get("instructor_note"),
            instructor_id             = row.get("instructor_id"),
            admin_note                = row.get("admin_note"),
            admin_id                  = row.get("admin_id"),
            submitted_at              = parse_dt(row.get("submitted_at")),
            reviewed_by_instructor_at = parse_dt(row.get("reviewed_by_instructor_at")),
            decided_by_admin_at       = parse_dt(row.get("decided_by_admin_at")),
        )

    def __repr__(self):
        return (
            f"PriorLearningRequest(id={self.id}, "
            f"learner={self.learner_id}, "
            f"course={self.course_code}, "
            f"status={self.status})"
        )