"""Tests for change request models."""

from cab.models.change import ChangeRequest, RiskScore, ApprovalStatus, ServiceContext


def test_change_request_defaults() -> None:
    req = ChangeRequest(service_name="payments-api")
    assert req.status == "draft"
    assert req.environment == "production"
    assert req.change_type == "standard"


def test_change_request_is_approved() -> None:
    req = ChangeRequest(service_name="payments-api", status="approved")
    assert req.is_approved is True
    assert req.can_deploy is True


def test_change_request_not_approved() -> None:
    req = ChangeRequest(service_name="payments-api", status="submitted")
    assert req.is_approved is False
    assert req.can_deploy is False


def test_change_request_emergency_process() -> None:
    req = ChangeRequest(service_name="payments-api", risk_level="critical")
    assert req.requires_emergency_process is True


def test_risk_score_levels() -> None:
    assert RiskScore.from_total(95, []).level == "critical"
    assert RiskScore.from_total(75, []).level == "high"
    assert RiskScore.from_total(50, []).level == "medium"
    assert RiskScore.from_total(20, []).level == "low"


def test_risk_score_capped_at_100() -> None:
    score = RiskScore.from_total(100, ["max score"])
    assert score.total == 100


def test_approval_status_defaults() -> None:
    status = ApprovalStatus(request_id="CHG0012345")
    assert status.status == "pending"
    assert status.approved_by == ""


def test_service_context_defaults() -> None:
    svc = ServiceContext(service_name="payments-api")
    assert svc.tier == 2
    assert svc.error_budget_remaining == 100.0
    assert svc.downstream_services == []