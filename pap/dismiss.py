"""Per-agent dismissed-topic state for proactive skills."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .state import load_json, save_json


DEFAULT_DB = Path("var/state/gate-dismissed.json")


def dismiss(
    agent: str,
    topic: str,
    terms: list[str],
    reason: str,
    *,
    dismissed_at: str | None = None,
    db_path: Path = DEFAULT_DB,
) -> dict[str, object]:
    """Record or update one dismissed topic, returning its entry."""
    if not agent.strip():
        raise ValueError("agent must not be empty")
    if not topic.strip():
        raise ValueError("topic must not be empty")
    cleaned_terms = [term.strip() for term in terms if term.strip()]
    if not cleaned_terms:
        raise ValueError("at least one term is required")
    if not reason.strip():
        raise ValueError("reason must not be empty")
    if dismissed_at is None:
        dismissed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    else:
        try:
            datetime.fromisoformat(dismissed_at)
        except ValueError as exc:
            raise ValueError(f"invalid dismissed date: {dismissed_at}") from exc

    state = load_json(db_path, {"agents": {}})
    agents = state.setdefault("agents", {})
    if not isinstance(agents, dict):
        raise ValueError(f"{db_path}: agents must be a JSON object")
    agent_state = agents.setdefault(agent, {"topics": {}})
    if not isinstance(agent_state, dict):
        raise ValueError(f"{db_path}: agent state must be a JSON object")
    topics = agent_state.setdefault("topics", {})
    if not isinstance(topics, dict):
        raise ValueError(f"{db_path}: topics must be a JSON object")

    entry: dict[str, object] = {
        "topic": topic,
        "terms": cleaned_terms,
        "reason": reason,
        "dismissed_at": dismissed_at,
    }
    topics[topic] = entry
    save_json(db_path, state)
    return entry


def dismissed(agent: str, *, db_path: Path = DEFAULT_DB) -> list[dict[str, object]]:
    """Return an agent's dismissed topics in deterministic topic order."""
    state = load_json(db_path, {"agents": {}})
    agents = state.get("agents", {})
    if not isinstance(agents, dict):
        raise ValueError(f"{db_path}: agents must be a JSON object")
    agent_state = agents.get(agent, {})
    if not isinstance(agent_state, dict):
        raise ValueError(f"{db_path}: agent state must be a JSON object")
    topics = agent_state.get("topics", {})
    if not isinstance(topics, dict):
        raise ValueError(f"{db_path}: topics must be a JSON object")
    return [topics[topic] for topic in sorted(topics)]
