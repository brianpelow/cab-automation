"""Nightly agent — generates sample CAB packages and validates risk scoring."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

REPO_ROOT = Path(__file__).parent.parent


def run_sample_cabs() -> None:
    from cab.core.config import CABConfig
    from cab.models.change import ServiceContext
    from cab.scorer.risk import score_change
    from cab.generator.package import generate_cab_package

    config = CABConfig()

    scenarios = [
        ("payments-api", 1, ["mobile-app", "web-frontend", "reporting"], 15.0, "standard", 120),
        ("fx-rate-service", 1, ["payments-api", "trading-engine"], 72.5, "dependency-update", 45),
        ("notification-service", 2, ["mobile-app"], 88.0, "new-feature", 200),
    ]

    results = []
    for svc_name, tier, downstream, budget, change_type, diff_lines in scenarios:
        svc = ServiceContext(
            service_id=f"SVC-{hash(svc_name) % 99999:05d}",
            service_name=svc_name,
            owner=f"team-{svc_name.split('-')[0]}@example.com",
            tier=tier,
            downstream_services=downstream,
            error_budget_remaining=budget,
            recent_incident_count=0,
        )
        risk = score_change(svc, change_type, diff_lines, config)
        package = generate_cab_package(
            svc, f"Routine {change_type} deployment of {svc_name}",
            risk, "production", change_type, config,
        )
        results.append({
            "service": svc_name,
            "risk_score": risk.total,
            "risk_level": risk.level,
            "request_id": package.request_id,
            "change_type": change_type,
        })

    out = REPO_ROOT / "docs" / "nightly-cab-samples.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": date.today().isoformat(),
        "sample_requests": results,
    }, indent=2))
    print(f"[agent] Generated {len(results)} sample CAB packages")
    for r in results:
        print(f"  {r['service']}: {r['risk_level']} ({r['risk_score']}/100)")


def refresh_changelog() -> None:
    changelog = REPO_ROOT / "CHANGELOG.md"
    if not changelog.exists():
        return
    today = date.today().isoformat()
    content = changelog.read_text()
    if today not in content:
        content = content.replace("## [Unreleased]", f"## [Unreleased]\n\n_Last run: {today}_", 1)
        changelog.write_text(content)
    print("[agent] Refreshed CHANGELOG timestamp")


if __name__ == "__main__":
    print(f"[agent] Starting nightly agent - {date.today().isoformat()}")
    run_sample_cabs()
    refresh_changelog()
    print("[agent] Done.")