"""
TicketIn Data Model (Headless Core Input Contract)

=============================================================================
WHAT CHANGED & WHY:
- Renamed class from Ticket_IN to TicketIn (standard PascalCase per PEP 8).
  Provided Ticket_IN alias for backward compatibility.
- Converted fields from UPPERCASE (TICKET_ID) to snake_case (ticket_id):
  1. Conforms to standard Pydantic v2 conventions and Python style.
  2. Aligns seamlessly with Rust Serde field naming without requiring manual
     #[serde(rename = "...")] tags in ai-workflow-gui.
- Changed ID types from int to `str | int`:
  1. Permits UUIDs, alphanumeric tokens, and session slugs (e.g., "sess_01").
  2. Maintains backward compatibility if a platform uses integer IDs.
- Retained working_state as `dict[str, Any] | None`:
  Platforms (Rust, REST APIs) manage state as plain JSON. Core is responsible
  for hydrating this raw dictionary into LangGraph message objects internally.
- Maintained platform responsibility:
  Fields remain required (no speculative defaults) because host platforms
  are responsible for constructing and providing valid execution boundaries.
=============================================================================
"""

from typing import Any

from pydantic import BaseModel, Field


class TicketIn(BaseModel):
    """
    Immutable execution ticket passed from a presentation platform into ColdWind Core.
    Represents a single conversational interaction turn.
    """

    ticket_id: str | int = Field(
        ...,
        description="Unique ticket ID for this execution turn (UUID or integer string)",
    )
    session_id: str | int = Field(
        ...,
        description="Session identifier for the conversation (UUID, slug, or integer)",
    )
    user_id: str | int = Field(
        ...,
        description="User identifier (OAuth subject, username, or integer)",
    )
    user_message: str = Field(
        ...,
        description="Raw user query or command for this turn",
    )
    working_state: dict[str, Any] | None = Field(
        default=None,
        description="Dehydrated conversation state from previous turn (plain JSON). None on first turn.",
    )
    allowed_tools: list[str] = Field(
        ...,
        description="List of tools the platform authorizes for this ticket execution",
    )
    limits: dict[str, Any] = Field(
        ...,
        description="Resource boundaries (e.g. timeout_seconds, max_iterations)",
    )


# Backward compatibility alias
Ticket_IN = TicketIn
