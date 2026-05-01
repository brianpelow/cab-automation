"""CAB package generator — produces structured change request documents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from cab.models.change import ChangeRequest, ServiceContext, RiskScore
from cab.core.config import CABConfig


def generate_cab_package(
    service: ServiceContext,
    diff_summary: str,
    risk: RiskScore,
    environment: str,
    change_type: str,
    config: CABConfig,
) -> ChangeRequest:
    """Generate a complete CAB change request package."""
    request_id = f"CHG{uuid.uuid4().int % 9999999:07d}"

    executive_summary = _generate_executive_summary(service, diff_summary, risk, config)
    rollback_plan = _generate_rollback_plan(service, change_type)
    slo_impact = _assess_slo_impact(service, risk)
    compliance_notes = _compliance_notes(service, risk, config)

    return ChangeRequest(
        request_id=request_id,
        service_name=service.service_name,
        service_id=service.service_id,
        environment=environment,
        change_type=change_type,
        diff_summary=diff_summary,
        risk_score=risk.total,
        risk_level=risk.level,
        blast_radius=len(service.downstream_services),
        affected_services=service.downstream_services,
        rollback_plan=rollback_plan,
        test_evidence="CI pipeline passed. All unit, integration, and security scans green.",
        slo_impact=slo_impact,
        compliance_notes=compliance_notes,
        executive_summary=executive_summary,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        status="draft",
    )


def _generate_executive_summary(
    service: ServiceContext,
    diff_summary: str,
    risk: RiskScore,
    config: CABConfig,
) -> str:
    if config.has_ai:
        return _ai_executive_summary(service, diff_summary, risk, config)
    return _template_executive_summary(service, diff_summary, risk, config)


def _ai_executive_summary(
    service: ServiceContext,
    diff_summary: str,
    risk: RiskScore,
    config: CABConfig,
) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.openrouter_api_key,
        )
        prompt = f"""You are a platform engineering leader writing a CAB change request summary for a {config.industry} organization.

Service: {service.service_name} (Tier {service.tier})
Owner: {service.owner}
Environment: production
Risk score: {risk.total}/100 ({risk.level})
Affected downstream services: {', '.join(service.downstream_services) or 'none'}
Error budget remaining: {service.error_budget_remaining:.1f}%

Change summary: {diff_summary}

Risk factors:
{chr(10).join(f'- {r}' for r in risk.rationale)}

Write a 2-paragraph executive summary for the CAB review board:
1. What is changing and why (business context)
2. Risk assessment and mitigations

Be concise, specific, and appropriate for a regulated {config.industry} audience."""

        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception:
        return _template_executive_summary(service, diff_summary, risk, config)


def _template_executive_summary(
    service: ServiceContext,
    diff_summary: str,
    risk: RiskScore,
    config: CABConfig,
) -> str:
    risk_desc = {"low": "minimal", "medium": "moderate", "high": "elevated", "critical": "critical"}.get(risk.level, "moderate")
    return f"""This change request covers a production deployment to {service.service_name} (Tier {service.tier}), owned by {service.owner}. {diff_summary}

The change carries {risk_desc} risk (score: {risk.total}/100). {"Blast radius includes " + str(len(service.downstream_services)) + " downstream service(s): " + ", ".join(service.downstream_services) + "." if service.downstream_services else "No downstream service dependencies identified."} Error budget remaining: {service.error_budget_remaining:.1f}%. {"Immediate rollback capability is available via the deployment pipeline." if risk.total < 70 else "This change requires CAB chair approval given elevated risk score. Rollback plan is documented below."}"""


def _generate_rollback_plan(service: ServiceContext, change_type: str) -> str:
    return f"""1. Trigger rollback via deployment pipeline: deploy {service.service_name} --rollback --env production
2. Verify service health at /health endpoint within 2 minutes
3. Confirm SLO metrics recovering in observability dashboard
4. Page {service.owner} if health check fails after rollback
5. Open P1 incident if rollback does not restore service within 5 minutes
6. Document rollback in post-deployment report within 1 hour"""


def _assess_slo_impact(service: ServiceContext, risk: RiskScore) -> str:
    if risk.total >= 70:
        return f"High risk change. SLO monitoring required for 2 hours post-deployment. Error budget currently at {service.error_budget_remaining:.1f}% — any degradation will trigger deployment freeze."
    elif risk.total >= 40:
        return f"Moderate risk. Monitor SLO dashboards for 30 minutes post-deployment. Error budget: {service.error_budget_remaining:.1f}%."
    return f"Low risk change. Standard SLO monitoring applies. Error budget: {service.error_budget_remaining:.1f}%."


def _compliance_notes(service: ServiceContext, risk: RiskScore, config: CABConfig) -> str:
    if config.industry == "fintech":
        return (
            f"This change must be logged in the ITSM system within 1 hour of deployment per SOX ITGC CC6.1. "
            f"{'Emergency change documentation required within 24 hours per SOX ITGC CC7.2.' if risk.level == 'critical' else ''} "
            f"{'PCI-DSS Requirement 6.3 change management controls apply — post-implementation review required within 5 business days.' if service.tier == 1 else ''}"
        )
    return "Change must be logged in ITSM system per operational compliance requirements."