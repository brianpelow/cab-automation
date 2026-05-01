"""Tests for CAB package generator."""

from cab.core.config import CABConfig
from cab.models.change import ServiceContext
from cab.scorer.risk import score_change
from cab.generator.package import generate_cab_package


def make_scenario(tier: int = 2, downstream: list | None = None) -> tuple:
    svc = ServiceContext(
        service_id="SVC-12345",
        service_name="payments-api",
        owner="team-payments@example.com",
        tier=tier,
        downstream_services=downstream or ["mobile-app"],
        error_budget_remaining=72.5,
        recent_incident_count=1,
    )
    config = CABConfig()
    risk = score_change(svc, "standard", 100, config)
    return svc, risk, config


def test_generate_package_returns_request() -> None:
    svc, risk, config = make_scenario()
    request = generate_cab_package(svc, "Deploy new payments feature", risk, "production", "standard", config)
    assert request.request_id.startswith("CHG")
    assert request.service_name == "payments-api"
    assert request.environment == "production"


def test_generated_package_has_required_fields() -> None:
    svc, risk, config = make_scenario()
    request = generate_cab_package(svc, "Deploy fix", risk, "production", "standard", config)
    assert request.rollback_plan != ""
    assert request.slo_impact != ""
    assert request.compliance_notes != ""
    assert request.executive_summary != ""
    assert request.submitted_at != ""


def test_high_risk_package_has_compliance_notes() -> None:
    svc, risk, config = make_scenario(tier=1, downstream=["mobile-app", "web-frontend", "reporting"])
    request = generate_cab_package(svc, "T1 service change", risk, "production", "standard", config)
    assert "SOX" in request.compliance_notes or "PCI" in request.compliance_notes


def test_package_risk_score_matches_scorer() -> None:
    svc, risk, config = make_scenario()
    request = generate_cab_package(svc, "test", risk, "production", "standard", config)
    assert request.risk_score == risk.total
    assert request.risk_level == risk.level