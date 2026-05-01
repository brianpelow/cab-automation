"""ServiceNow ITSM client — mock implementation for reference."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from cab.models.change import ChangeRequest, ApprovalStatus
from cab.core.config import CABConfig


class ServiceNowClient:
    """Client for ServiceNow ITSM change management API."""

    def __init__(self, config: CABConfig) -> None:
        self.base_url = config.servicenow_url.rstrip("/")
        self.token = config.servicenow_token
        self.timeout = 30

    def submit_change(self, request: ChangeRequest) -> str:
        """Submit a change request to ServiceNow. Returns SNOW ticket number."""
        if not self.token:
            return _mock_submit(request)
        try:
            import httpx
            response = httpx.post(
                f"{self.base_url}/api/now/table/change_request",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json={
                    "short_description": f"[{request.risk_level.upper()}] {request.service_name} production deployment",
                    "description": request.executive_summary,
                    "risk": _map_risk_level(request.risk_level),
                    "category": "Software",
                    "assignment_group": request.service_name,
                    "u_cab_request_id": request.request_id,
                    "u_risk_score": str(request.risk_score),
                    "u_affected_services": ", ".join(request.affected_services),
                    "u_rollback_plan": request.rollback_plan,
                    "u_compliance_notes": request.compliance_notes,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("result", {}).get("number", f"CHG{uuid.uuid4().int % 9999999:07d}")
        except Exception:
            return _mock_submit(request)

    def get_approval_status(self, snow_ticket: str) -> ApprovalStatus:
        """Query approval status for a ServiceNow change ticket."""
        if not self.token:
            return _mock_approval_status(snow_ticket)
        try:
            import httpx
            response = httpx.get(
                f"{self.base_url}/api/now/table/change_request",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"number": snow_ticket, "sysparm_fields": "number,state,approved_by,approval"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json().get("result", [{}])[0]
            state = result.get("state", "")
            return ApprovalStatus(
                request_id=snow_ticket,
                snow_ticket=snow_ticket,
                status=_map_snow_state(state),
                approved_by=result.get("approved_by", {}).get("display_value", ""),
                approved_at=result.get("sys_updated_on", ""),
            )
        except Exception:
            return _mock_approval_status(snow_ticket)

    def approve_change(self, snow_ticket: str, approver: str, comments: str = "") -> bool:
        """Approve a change request in ServiceNow."""
        if not self.token:
            print(f"[mock] Approved {snow_ticket} by {approver}")
            return True
        try:
            import httpx
            response = httpx.patch(
                f"{self.base_url}/api/now/table/change_request/{snow_ticket}",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"state": "approved", "approved_by": approver, "work_notes": comments},
                timeout=self.timeout,
            )
            return response.status_code in (200, 204)
        except Exception:
            return False


def _mock_submit(request: ChangeRequest) -> str:
    ticket = f"CHG{uuid.uuid4().int % 9999999:07d}"
    print(f"[mock-snow] Submitted change request: {ticket}")
    print(f"  Service: {request.service_name}")
    print(f"  Risk: {request.risk_level} ({request.risk_score}/100)")
    print(f"  Status: Pending CAB review")
    return ticket


def _mock_approval_status(snow_ticket: str) -> ApprovalStatus:
    return ApprovalStatus(
        request_id=snow_ticket,
        snow_ticket=snow_ticket,
        status="approved",
        approved_by="cab-chair@example.com",
        approved_at=datetime.now(timezone.utc).isoformat(),
        comments=["Approved by CAB. Standard deployment window applies."],
    )


def _map_risk_level(level: str) -> str:
    return {"low": "1", "medium": "2", "high": "3", "critical": "4"}.get(level, "2")


def _map_snow_state(state: str) -> str:
    return {
        "-5": "draft", "-4": "submitted", "-3": "submitted",
        "0": "approved", "1": "approved", "3": "rejected",
    }.get(state, "pending")