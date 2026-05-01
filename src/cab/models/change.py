"""Change request data models."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone


class ServiceContext(BaseModel):
    """Service context from Service Registry."""

    service_id: str = ""
    service_name: str
    owner: str = ""
    tier: int = 2
    downstream_services: list[str] = Field(default_factory=list)
    error_budget_remaining: float = 100.0
    recent_incident_count: int = 0


class ChangeRequest(BaseModel):
    """A CAB change request."""

    request_id: str = ""
    service_name: str
    service_id: str = ""
    environment: str = Field("production", description="Target deployment environment")
    change_type: str = Field("standard", description="standard/emergency/normal")
    summary: str = ""
    diff_summary: str = ""
    risk_score: int = 0
    risk_level: str = Field("low", description="low/medium/high/critical")
    blast_radius: int = 0
    affected_services: list[str] = Field(default_factory=list)
    rollback_plan: str = ""
    test_evidence: str = ""
    slo_impact: str = ""
    compliance_notes: str = ""
    executive_summary: str = ""
    submitted_at: str = ""
    status: str = Field("draft", description="draft/submitted/approved/rejected/implemented")
    snow_ticket: str = ""
    approved_by: str = ""
    approved_at: str = ""

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def can_deploy(self) -> bool:
        return self.status in ("approved", "implemented")

    @property
    def requires_emergency_process(self) -> bool:
        return self.risk_level == "critical" or self.change_type == "emergency"


class RiskScore(BaseModel):
    """Detailed risk score breakdown."""

    total: int = 0
    tier_score: int = 0
    blast_radius_score: int = 0
    error_budget_score: int = 0
    change_type_score: int = 0
    deploy_time_score: int = 0
    incident_history_score: int = 0
    level: str = "low"
    rationale: list[str] = Field(default_factory=list)

    @classmethod
    def from_total(cls, total: int, rationale: list[str]) -> "RiskScore":
        level = "critical" if total >= 90 else "high" if total >= 70 else "medium" if total >= 40 else "low"
        return cls(total=total, level=level, rationale=rationale)


class ApprovalStatus(BaseModel):
    """Current approval status from ServiceNow."""

    request_id: str
    snow_ticket: str = ""
    status: str = "pending"
    approved_by: str = ""
    approved_at: str = ""
    rejection_reason: str = ""
    comments: list[str] = Field(default_factory=list)