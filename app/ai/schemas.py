"""Structured Pydantic schemas for classification, agent responses, and deterministic decisions."""

from typing import Literal

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """Structured details of customer problem or product issue."""

    topic: str = Field(
        description="General problem topic, e.g. sizing, leak, missing-part, damaged-part"
    )
    product: str | None = Field(
        default=None, description="Product type, e.g. paddle-board or shelving"
    )
    model_code: str | None = Field(
        default=None, description="Model code, e.g. 10'6, 11', HP-S3, HP-C4"
    )
    size: str | None = Field(default=None, description="Specified size or rider weight")
    order_number: str | None = Field(
        default=None, description="Extracted Amazon order number if present"
    )
    part_number: str | None = Field(
        default=None, description="Specific panel or part number, e.g. HP-S3-04"
    )
    finish: str | None = Field(
        default=None, description="Finish/color, e.g. natural oak, white, walnut"
    )
    details: str = Field(default="", description="Summary of specific issue facts")


class Classification(BaseModel):
    """Output schema for ticket classification."""

    section: str = Field(
        description="Relevant knowledge base section: paddle-boards, shelving, returns-and-warranty, shipping, brand-and-tone, escalation-rules"
    )
    language: str = Field(
        default="en", description="ISO 639-1 language code, e.g. en, de, fr, es, hi"
    )
    needs_human: bool = Field(
        description="True if email requires human intervention based on policy"
    )
    reason: str = Field(
        description="Brief explanation of classification or escalation rationale"
    )
    acknowledgement: str = Field(
        description="Safe, polite acknowledgement note addressing the customer appropriately"
    )


class AgentReply(BaseModel):
    """Output schema for AI agent drafting customer replies."""

    action: Literal["reply", "escalate"] = Field(
        description="Proposed course of action: reply with answer or escalate to human"
    )
    reply: str = Field(
        description="Drafted email response text or escalation acknowledgement"
    )
    reasoning: str = Field(
        description="Internal reasoning behind the proposed reply or escalation"
    )
    enough_information: bool = Field(
        description="True if the request contained sufficient details to resolve according to policy"
    )
    promises_an_action: bool = Field(
        default=False,
        description="True if the reply explicitly promises an action (shipment, refund, replacement, date)",
    )
    issue: Issue | None = Field(
        default=None, description="Extracted issue entities if applicable"
    )


class Decision(BaseModel):
    """Final, validated, deterministic system decision."""

    action: Literal["reply", "escalate"] = Field(
        description="Final action: reply or escalate"
    )
    section: str = Field(description="Knowledge base section category")
    reply: str = Field(description="Final email text to send to customer")
    reason: str = Field(description="Auditable decision rationale")
    proposed_action: str | None = Field(
        default=None,
        description="Internal proposed operational action: ask-details, valve-check, ship-part, ship-hardware-kit, ship-panels, new-board, patch-kit, full-replacement, exchange, escalate",
    )
