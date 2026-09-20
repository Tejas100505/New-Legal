"""
Health-check response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """Status of a single dependency (database, Redis, etc.)."""
    name: str = Field(..., description="Dependency name", examples=["postgresql"])
    status: str = Field(..., description="up or down", examples=["up"])
    latency_ms: float | None = Field(
        None, description="Round-trip latency in milliseconds"
    )
    error: str | None = Field(None, description="Error message if down")


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""
    status: str = Field(..., description="Overall health status", examples=["healthy"])
    version: str = Field(..., description="Application version", examples=["1.0.0"])
    environment: str = Field(..., description="Running environment", examples=["development"])
    uptime_seconds: float = Field(..., description="Seconds since startup")
    dependencies: list[DependencyStatus] = Field(
        default_factory=list, description="Status of each dependency"
    )
