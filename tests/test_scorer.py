"""Tests for risk scorer."""

from cab.core.config import CABConfig
from cab.models.change import ServiceContext
from cab.scorer.risk import score_change, _get_deploy_window


def make_service(tier: int = 2, downstream: int = 0, budget: float = 80.0, incidents: int = 0) -> ServiceContext:
    return ServiceContext(
        service_id="SVC-12345",
        service_name="test-service",
        owner="team@example.com",
        tier=tier,
        downstream_services=[f"svc-{i}" for i in range(downstream)],
        error_budget_remaining=budget,
        recent_incident_count=incidents,
    )


def test_tier1_scores_higher_than_tier3() -> None:
    config = CABConfig()
    t1 = score_change(make_service(tier=1), "standard", 0, config)
    t3 = score_change(make_service(tier=3), "standard", 0, config)
    assert t1.total > t3.total


def test_critical_error_budget_increases_score() -> None:
    config = CABConfig()
    healthy = score_change(make_service(budget=90.0), "standard", 0, config)
    critical = score_change(make_service(budget=5.0), "standard", 0, config)
    assert critical.total > healthy.total


def test_downstream_services_increase_score() -> None:
    config = CABConfig()
    no_deps = score_change(make_service(downstream=0), "standard", 0, config)
    many_deps = score_change(make_service(downstream=5), "standard", 0, config)
    assert many_deps.total > no_deps.total


def test_emergency_change_type_scores_higher() -> None:
    config = CABConfig()
    standard = score_change(make_service(), "standard", 0, config)
    emergency = score_change(make_service(), "emergency", 0, config)
    assert emergency.total > standard.total


def test_incidents_increase_score() -> None:
    config = CABConfig()
    clean = score_change(make_service(incidents=0), "standard", 0, config)
    incidents = score_change(make_service(incidents=3), "standard", 0, config)
    assert incidents.total > clean.total


def test_score_never_exceeds_100() -> None:
    config = CABConfig()
    score = score_change(make_service(tier=1, downstream=10, budget=2.0, incidents=5), "emergency", 600, config)
    assert score.total <= 100


def test_score_has_rationale() -> None:
    config = CABConfig()
    score = score_change(make_service(tier=1), "standard", 0, config)
    assert len(score.rationale) > 0


def test_get_deploy_window_returns_string() -> None:
    window = _get_deploy_window()
    assert window in ("friday-pm", "weekend", "monday-am", "business-hours", "off-hours")