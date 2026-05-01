"""Approval gate FastAPI service — blocks production deploys until CAB approved."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cab.core.config import CABConfig
from cab.models.change import ChangeRequest, ApprovalStatus
from cab.servicenow.client import ServiceNowClient

app = FastAPI(
    title="CAB Approval Gate",
    description="Deployment gate — blocks production until CAB approval received",
    version="0.1.0",
)

config = CABConfig.from_env()
_requests: dict[str, ChangeRequest] = {}


class GateCheckRequest(BaseModel):
    service_name: str
    environment: str
    request_id: str = ""
    snow_ticket: str = ""


class GateCheckResponse(BaseModel):
    allowed: bool
    reason: str
    request_id: str = ""
    snow_ticket: str = ""
    risk_level: str = ""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/gate/check", response_model=GateCheckResponse)
def check_deployment_gate(req: GateCheckRequest) -> GateCheckResponse:
    """Check if a deployment is approved to proceed."""
    if req.environment != "production":
        return GateCheckResponse(
            allowed=True,
            reason=f"Non-production environment '{req.environment}' — CAB not required",
        )

    if req.snow_ticket:
        client = ServiceNowClient(config)
        status = client.get_approval_status(req.snow_ticket)
        if status.status == "approved":
            return GateCheckResponse(
                allowed=True,
                reason=f"CAB approved by {status.approved_by}",
                snow_ticket=req.snow_ticket,
            )
        elif status.status == "rejected":
            return GateCheckResponse(
                allowed=False,
                reason=f"CAB rejected: {status.rejection_reason or 'See ServiceNow for details'}",
                snow_ticket=req.snow_ticket,
            )
        else:
            return GateCheckResponse(
                allowed=False,
                reason=f"CAB approval pending (status: {status.status}). Submit: cab submit --service {req.service_name}",
                snow_ticket=req.snow_ticket,
            )

    return GateCheckResponse(
        allowed=False,
        reason=f"No CAB request found for {req.service_name}. Submit: cab submit --service {req.service_name} --env production",
    )


@app.post("/gate/register")
def register_change_request(request: ChangeRequest) -> dict:
    """Register a change request with the gate."""
    _requests[request.request_id] = request
    return {"registered": True, "request_id": request.request_id}


@app.get("/gate/requests")
def list_pending_requests() -> dict:
    pending = [r for r in _requests.values() if r.status in ("submitted", "draft")]
    return {"count": len(pending), "requests": [r.model_dump() for r in pending]}


def run() -> None:
    import uvicorn
    uvicorn.run("cab.api.gate:app", host="0.0.0.0", port=8002, reload=False)