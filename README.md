# cab-automation

> Change Advisory Board automation — AI-generated CAB packages, risk scoring, and deployment gates for regulated financial services.

![CI](https://github.com/brianpelow/cab-automation/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)

## Overview

`cab-automation` eliminates the manual bottleneck in regulated change management.
Instead of engineers filling out Word document templates, the control plane
generates CAB request packages automatically from git diffs, Service Registry
dependency data, and CI pipeline results — then blocks deployment until approval
is received from ServiceNow.

Built for platform engineering teams in regulated financial services and
manufacturing where change management is a top SOX ITGC and PCI-DSS audit
finding area.

## The problem

Manual CAB process in regulated organizations:
- Engineers fill out Word templates from memory
- Risk scores are subjective and inconsistent
- Dependency maps are outdated or missing
- 2-5 day approval cycle blocks delivery
- Teams game the system or skip changes entirely
- Results in SOX audit findings

## The solution

```
git push
  -> orbit-platform validates and builds
  -> cab-automation generates CAB package from git diff + Service Registry
  -> cab-automation scores risk via OPA policy engine
  -> cab-automation submits to ServiceNow
  -> Deployment blocked until CAB approval received
  -> Full audit trail committed to Git
```

## Components

| Component | Description |
|-----------|-------------|
| Risk Scorer | OPA-based risk scoring 1-100 using service tier, blast radius, error budget, time of day |
| CAB Package Generator | AI-generated change request with executive summary, rollback plan, SLO impact |
| ServiceNow Client | Mock ITSM integration — submit, query, approve, reject |
| Approval Gate | FastAPI deployment gate — blocks production deploy until CAB approved |
| Emergency Handler | Expedited P0 path with post-hoc documentation and full audit trail |
| CAB CLI | cab submit, cab status, cab approve, cab emergency |

## Risk scoring factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Service tier | High | T1 payment services score higher than T3 internal tools |
| Blast radius | High | Number of downstream dependent services |
| Error budget | High | Changes blocked if < 10% budget remaining |
| Change type | Medium | New feature vs dependency update vs config change |
| Deploy time | Medium | Friday deploys score higher than Tuesday morning |
| Incident history | Medium | Recent incidents increase risk score |

## Quick start

```bash
pip install cab-automation

cab submit --service payments-api --diff ./changes.diff --env production
cab status --request-id CHG0012345
cab emergency --service payments-api --incident INC0098765
```

## Integration with orbit-platform

cab-automation plugs into Step 6 (DEPLOY) of the orbit-platform control flow.
The approval gate API is called before any production deployment proceeds.

## Contributing

See CONTRIBUTING.md.

## License

Apache 2.0
