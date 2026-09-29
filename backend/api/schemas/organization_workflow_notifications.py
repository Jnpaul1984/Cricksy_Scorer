"""Bounded results for manual cricket workflow notification actions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class OrganizationEventNotificationRequest(BaseModel):
    notification_type: Literal["update", "cancellation"]

    model_config = ConfigDict(extra="forbid")


class OrganizationWorkflowDeliveryResult(BaseModel):
    source_type: Literal["organization_event", "selection_publication", "availability_target"]
    source_id: str
    source_version: str
    safe_user_recipient_count: int
    delivered_count: int
    suppressed_by_preference_count: int
    unresolved_roster_recipient_count: int


class OrganizationEventNotificationResult(OrganizationWorkflowDeliveryResult):
    notification_type: Literal["update", "cancellation"]


class OrganizationSelectionNotificationResult(OrganizationWorkflowDeliveryResult):
    selection_plan_id: str
    publication_version: int
    xi_roster_count: int
    reserve_roster_count: int
    unresolved_xi_count: int
    unresolved_reserve_count: int


class OrganizationAvailabilityReminderResult(OrganizationWorkflowDeliveryResult):
    target_type: Literal["event", "fixture"]
    no_response_count: int
