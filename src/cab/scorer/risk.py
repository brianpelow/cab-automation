"""OPA-based risk scorer for change requests."""

from __future__ import annotations

from datetime import datetime, timezone
from cab.models.change import ServiceContext, RiskScore
from cab.core.config import CABConfig


TIER_SCORES = {1: 30, 2: 15, 3: 5}
CHANGE_TYPE_SCORES = {"new-feature": 20, "dependency-update": 10, "config-change": 15, "hotfix": 25, "standard": 10, "emergency": 25}
DEPLOY_WINDOW_SCORES = {
    "friday-pm": 20, "weekend": 25, "monday-am": 5,
    "business-hours": 0, "off-hours": 10,
}


def score_change(
    service: ServiceContext,
    change_type: str,
    diff_lines: int,
    config: CABConfig,
) -> RiskScore:
    """Compute a risk score 0-100 for a proposed change."""
    rationale = []
    total = 0

    tier_score = TIER_SCORES.get(service.tier, 10)
    total += tier_score
    rationale.append(f"Service tier {service.tier}: +{tier_score} points")

    blast = min(len(service.downstream_services) * 8, 25)
    total += blast
    if blast > 0:
        rationale.append(f"Blast radius ({len(service.downstream_services)} downstream services): +{blast} points")

    budget_score = 0
    if service.error_budget_remaining < 10:
        budget_score = 25
        rationale.append(f"Error budget critical ({service.error_budget_remaining:.1f}% remaining): +{budget_score} points")
    elif service.error_budget_remaining < 25:
        budget_score = 15
        rationale.append(f"Error budget low ({service.error_budget_remaining:.1f}% remaining): +{budget_score} points")
    elif service.error_budget_remaining < 50:
        budget_score = 5
        rationale.append(f"Error budget moderate ({service.error_budget_remaining:.1f}% remaining): +{budget_score} points")
    total += budget_score

    ct_score = CHANGE_TYPE_SCORES.get(change_type, 10)
    total += ct_score
    rationale.append(f"Change type '{change_type}': +{ct_score} points")

    window = _get_deploy_window()
    window_score = DEPLOY_WINDOW_SCORES.get(window, 0)
    total += window_score
    if window_score > 0:
        rationale.append(f"Deploy window '{window}': +{window_score} points")

    incident_score = min(service.recent_incident_count * 5, 15)
    total += incident_score
    if incident_score > 0:
        rationale.append(f"Recent incidents ({service.recent_incident_count}): +{incident_score} points")

    size_score = 0
    if diff_lines > 500:
        size_score = 10
        rationale.append(f"Large diff ({diff_lines} lines): +{size_score} points")
    elif diff_lines > 200:
        size_score = 5
        rationale.append(f"Medium diff ({diff_lines} lines): +{size_score} points")
    total += size_score

    total = min(total, 100)

    score = RiskScore.from_total(total, rationale)
    score.tier_score = tier_score
    score.blast_radius_score = blast
    score.error_budget_score = budget_score
    score.change_type_score = ct_score
    score.deploy_time_score = window_score
    score.incident_history_score = incident_score
    return score


def _get_deploy_window() -> str:
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    hour = now.hour

    if weekday >= 5:
        return "weekend"
    if weekday == 4 and hour >= 12:
        return "friday-pm"
    if weekday == 0 and hour < 10:
        return "monday-am"
    if 9 <= hour <= 17:
        return "business-hours"
    return "off-hours"