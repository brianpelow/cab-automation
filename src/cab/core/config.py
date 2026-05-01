"""Configuration for cab-automation."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


class CABConfig(BaseModel):
    """Runtime configuration for CAB automation."""

    openrouter_api_key: str = Field("", description="OpenRouter API key")
    servicenow_url: str = Field("https://mock-snow.example.com", description="ServiceNow instance URL")
    servicenow_token: str = Field("", description="ServiceNow API token")
    orbit_registry_url: str = Field("http://localhost:8001", description="Orbit Service Registry URL")
    industry: str = Field("fintech", description="Industry context")
    high_risk_threshold: int = Field(70, description="Risk score threshold for standard CAB review")
    critical_risk_threshold: int = Field(90, description="Risk score threshold for emergency CAB")
    blocked_deploy_windows: list[str] = Field(
        default_factory=lambda: ["friday-pm", "weekend"],
        description="Time windows where deployments are blocked by default",
    )

    @classmethod
    def from_env(cls) -> "CABConfig":
        return cls(
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            servicenow_url=os.environ.get("SNOW_URL", "https://mock-snow.example.com"),
            servicenow_token=os.environ.get("SNOW_TOKEN", ""),
            industry=os.environ.get("CAB_INDUSTRY", "fintech"),
        )

    @property
    def has_ai(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def has_servicenow(self) -> bool:
        return bool(self.servicenow_token)