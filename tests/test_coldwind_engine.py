"""
Unit and integration tests for ColdWindEngine headless facade.
Validates boot lifecycle, stateless ticket processing, fail-fast validation,
error boundaries, and graceful teardown.
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from coldwind.core.engine.coldwind_engine import ColdWindEngine, RuntimeTicketError
from coldwind.core.models.ticket_in import TicketIn
from coldwind.core.models.ticket_out import TicketOut
from coldwind.core.runtime import ContextRegistry
from coldwind.core.system_logging.on_time_registry import OnTimeRegistry
from coldwind.desktop.config.DesktopConfig import DesktopConfig
from coldwind.desktop.runtime.DesktopContext import DesktopRunTimeContext


@pytest.fixture(autouse=True)
def setup_desktop_runtime_context():
    """Ensure an active runtime context is registered for engine execution and clean up handlers."""
    config = DesktopConfig(project_root=Path.cwd())
    context = DesktopRunTimeContext(config)
    ContextRegistry.activate_context(context, force=True)
    yield context
    # Clean up singleton logging handlers between tests to maintain test isolation
    OnTimeRegistry()._handlers.clear()


def test_engine_unbooted_fails_fast():
    """Verify processing tickets before boot raises RuntimeTicketError."""
    engine = ColdWindEngine()
    assert not engine._is_booted

    ticket = TicketIn(
        ticket_id="ticket-001",
        session_id="session-001",
        user_id="user-001",
        user_message="Hello",
        working_state=None,
        allowed_tools=[],
        limits={},
    )

    with pytest.raises(RuntimeTicketError, match="Environment not satisfied"):
        engine.process_ticket(ticket)


def test_engine_boot_and_shutdown():
    """Verify engine boots, registers components, and shuts down cleanly."""
    engine = ColdWindEngine()
    engine.boot()

    assert engine._is_booted is True
    assert engine._graph is not None

    engine.shutdown()
    assert engine._is_booted is False


def test_process_ticket_empty_user_message_fails_fast():
    """Verify empty user_message immediately fails without processing."""
    engine = ColdWindEngine()
    engine.boot()

    ticket = TicketIn(
        ticket_id="ticket-002",
        session_id="session-001",
        user_id="user-001",
        user_message="",
        working_state=None,
        allowed_tools=[],
        limits={},
    )

    with pytest.raises(RuntimeTicketError, match="user_message cannot be empty"):
        engine.process_ticket(ticket)


def test_process_ticket_malformed_working_state_fails_fast():
    """Verify invalid messages in working_state fail immediately without silent fallback."""
    engine = ColdWindEngine()
    engine.boot()

    ticket_bad_format = TicketIn(
        ticket_id="ticket-003",
        session_id="session-001",
        user_id="user-001",
        user_message="Test",
        working_state={"messages": [12345]},
        allowed_tools=[],
        limits={},
    )

    with pytest.raises(RuntimeTicketError, match="Unsupported message format"):
        engine.process_ticket(ticket_bad_format)

    ticket_bad_role = TicketIn(
        ticket_id="ticket-004",
        session_id="session-001",
        user_id="user-001",
        user_message="Test",
        working_state={"messages": [{"role": "unrecognized_role", "content": "hello"}]},
        allowed_tools=[],
        limits={},
    )

    with pytest.raises(RuntimeTicketError, match="Unsupported message role"):
        engine.process_ticket(ticket_bad_role)

    ticket_missing_keys = TicketIn(
        ticket_id="ticket-005",
        session_id="session-001",
        user_id="user-001",
        user_message="Test",
        working_state={"messages": [{"type": "human"}]},  # Missing content
        allowed_tools=[],
        limits={},
    )

    with pytest.raises(RuntimeTicketError, match="Malformed ticket message"):
        engine.process_ticket(ticket_missing_keys)


def test_process_ticket_happy_path_with_mock_graph():
    """Verify end-to-end single-turn ticket execution, O(1) transcript extraction, and TicketOut."""
    engine = ColdWindEngine()
    engine.boot()

    # Mock the internal graph to avoid external API / network dependency
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "messages": [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer"),
            HumanMessage(content="How are you?"),
            AIMessage(content="I am doing well, ready to help!"),
        ],
        "message_type": "llm",
    }
    engine._graph = mock_graph

    ticket = TicketIn(
        ticket_id="ticket-006",
        session_id="session-001",
        user_id="user-001",
        user_message="How are you?",
        working_state={
            "messages": [
                {"role": "user", "content": "Previous question"},
                {"type": "ai", "content": "Previous answer"},
            ],
            "message_type": "llm",
        },
        allowed_tools=[],
        limits={},
    )

    out: TicketOut = engine.process_ticket(ticket)

    assert out.status == "COMPLETED"
    assert out.ticket_id == "ticket-006"
    assert out.transcript == "I am doing well, ready to help!"
    assert out.error_info is None
    assert out.usage["message_count"] == 4
    assert out.usage["latency_ms"] >= 0.0

    # Ensure serialization to JSON works cleanly
    json_payload = out.model_dump_json()
    assert "ticket-006" in json_payload
    assert "COMPLETED" in json_payload


def test_process_ticket_graph_exception_handled():
    """Verify runtime graph execution failure produces TicketOut(status='FAILED') cleanly."""
    engine = ColdWindEngine()
    engine.boot()

    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = RuntimeError("Simulated graph LLM failure")
    engine._graph = mock_graph

    ticket = TicketIn(
        ticket_id="ticket-007",
        session_id="session-001",
        user_id="user-001",
        user_message="Trigger error",
        working_state=None,
        allowed_tools=[],
        limits={},
    )

    out: TicketOut = engine.process_ticket(ticket)

    assert out.status == "FAILED"
    assert out.ticket_id == "ticket-007"
    assert out.transcript == ""
    assert out.error_info is not None
    assert "Simulated graph LLM failure" in out.error_info["error"]
    assert out.error_info["type"] == "RuntimeError"
