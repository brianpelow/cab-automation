"""Tests for ServiceNow client."""

from cab.core.config import CABConfig
from cab.models.change import ChangeRequest
from cab.servicenow.client import ServiceNowClient, _mock_submit, _mock_approval_status


def test_mock_submit_returns_ticket() -> None:
    request = ChangeRequest(
        service_name="payments-api",
        risk_level="medium",
        risk_score=45,
    )
    ticket = _mock_submit(request)
    assert ticket.startswith("CHG")
    assert len(ticket) == 10


def test_mock_approval_status_approved() -> None:
    status = _mock_approval_status("CHG0012345")
    assert status.status == "approved"
    assert status.approved_by != ""


def test_client_submit_no_token() -> None:
    config = CABConfig()
    client = ServiceNowClient(config)
    request = ChangeRequest(service_name="test-service", risk_level="low", risk_score=20)
    ticket = client.submit_change(request)
    assert ticket.startswith("CHG")


def test_client_get_status_no_token() -> None:
    config = CABConfig()
    client = ServiceNowClient(config)
    status = client.get_approval_status("CHG0012345")
    assert status.status in ("approved", "pending", "rejected", "submitted")


def test_client_approve_no_token() -> None:
    config = CABConfig()
    client = ServiceNowClient(config)
    result = client.approve_change("CHG0012345", "cab-chair@example.com")
    assert result is True