"""Small contextvars-based public API for paplog."""
from __future__ import annotations

import contextvars
import os
import traceback
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from pathlib import Path
from typing import Any, Mapping

from .core import Ledger, git_provenance, node_id, span_id, trace_id, ulid

_ledger: Ledger | None = None
_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("paplog_context", default={})


def configure(directory: str | os.PathLike[str] | None = None) -> Ledger:
    global _ledger
    _ledger = Ledger(directory)
    return _ledger


def get_ledger() -> Ledger:
    global _ledger
    if _ledger is None: _ledger = Ledger()
    return _ledger


def current() -> dict[str, Any]:
    return dict(_context.get())


def _ambient_context() -> dict[str, Any]:
    """Decode context propagated by a PAP parent process, if present.

    A direct point event in a child runtime may have no enclosing Python scope.
    It must still attach to the parent run/operation rather than become a new
    trace just because the child is a separate process.
    """
    traceparent = os.environ.get("TRACEPARENT", "").split("-")
    trace: dict[str, Any] = {}
    if len(traceparent) == 4 and len(traceparent[1]) == 32 and len(traceparent[2]) == 16:
        trace = {"trace_id": traceparent[1], "parent_span_id": traceparent[2]}
    execution = {key: value for key, value in {
        "run_id": os.environ.get("PAP_RUN_ID"),
        "operation_id": os.environ.get("PAP_PARENT_OPERATION_ID"),
        "node_id": os.environ.get("PAP_NODE_ID"),
    }.items() if value}
    result: dict[str, Any] = {"trace": trace, "execution": execution}
    if agent := (os.environ.get("PAP_AGENT") or os.environ.get("PAP_AGENT_ID")):
        result["agent"] = {"id": agent}
    if skill := os.environ.get("PAP_SKILL"):
        result["skill"] = {"id": skill}
    if job := os.environ.get("PAP_JOB_ID"):
        result["job"] = {"id": job}
    backend, mode = os.environ.get("PAP_RUNTIME_BACKEND"), os.environ.get("PAP_RUNTIME_MODE")
    if backend or mode:
        result["runtime"] = {"backend": backend or "direct", "mode": mode or "manual"}
    return result


def _merge(metadata: Mapping[str, Any]) -> dict[str, Any]:
    parent = current() or _ambient_context()
    trace = dict(parent.get("trace", {})); execution = dict(parent.get("execution", {}))
    merged = {"trace": trace, "execution": execution, **metadata}
    for key in ("job", "agent", "skill", "context", "runtime", "repository", "git_commit", "git_branch", "git_dirty"):
        if key not in merged and parent.get(key): merged[key] = parent[key]
    return merged


def event(event_name: str, *, subject: Mapping[str, Any] | None = None, attributes: Mapping[str, Any] | None = None, links: list[Mapping[str, Any]] | None = None, severity: str = "INFO", kind: str = "event", **metadata: Any) -> dict[str, Any]:
    record = _merge(metadata)
    # Point events can be emitted at an existing integration boundary without
    # an enclosing context manager. They still need trace identity so querying
    # a run/trace never produces orphaned semantic facts.
    record["trace"].setdefault("trace_id", trace_id())
    record["trace"].setdefault("span_id", span_id())
    record.update({"event_name": event_name, "kind": kind, "severity": severity, "subject": dict(subject or {}), "attributes": dict(attributes or {}), "links": list(links or [])})
    return get_ledger().emit(record)


class _Scope(AbstractContextManager["_Scope"], AbstractAsyncContextManager["_Scope"]):
    def __init__(self, event_name: str, *, kind: str, effect: str | None = None, scope: str | None = None, **metadata: Any):
        self.event_name, self.kind, self.metadata = event_name, kind, metadata
        self.effect, self.scope, self.token, self.started, self.context = effect, scope, None, None, None

    def __enter__(self) -> "_Scope":
        parent = current() or _ambient_context()
        trace = dict(parent.get("trace", {})); execution = dict(parent.get("execution", {}))
        trace.setdefault("trace_id", os.environ.get("TRACEPARENT", "").split("-")[1] if os.environ.get("TRACEPARENT", "").count("-") >= 3 else trace_id())
        trace["parent_span_id"] = trace.get("span_id")
        trace["span_id"] = span_id()
        execution.setdefault("run_id", os.environ.get("PAP_RUN_ID") or ulid())
        if self.kind == "action":
            # Actions are children of the current operation. Keep the parent
            # operation identity and allocate a distinct action identity.
            execution.setdefault("operation_id", parent.get("execution", {}).get("operation_id"))
            execution["action_id"] = ulid()
            if not execution.get("operation_id"):
                execution["operation_id"] = ulid()
        else:
            execution["operation_id"] = ulid()
        execution.setdefault("node_id", os.environ.get("PAP_NODE_ID") or node_id())
        # Accept the concise public API (`job_id=`, `agent=`, `skill=`) while
        # retaining the canonical object-shaped event envelope internally.
        if self.metadata.get("job_id") and not self.metadata.get("job"):
            self.metadata["job"] = {"id": self.metadata["job_id"]}
        if isinstance(self.metadata.get("agent"), str):
            self.metadata["agent"] = {"id": self.metadata["agent"]}
        if isinstance(self.metadata.get("skill"), str):
            self.metadata["skill"] = {"id": self.metadata["skill"]}
        runtime = self.metadata.pop("runtime", parent.get("runtime", {"backend": os.environ.get("PAP_RUNTIME_BACKEND", "direct"), "mode": os.environ.get("PAP_RUNTIME_MODE", "manual")}))
        provenance = git_provenance(Path.cwd())
        self.context = {**parent, **self.metadata, "trace": trace, "execution": execution, "runtime": runtime, **provenance}
        self.token = _context.set(self.context)
        self.started = __import__("time").monotonic()
        attributes = dict(self.metadata.pop("attributes", {}))
        if self.kind == "action": attributes.update({"action.effect": self.effect, "action.scope": self.scope})
        self.context["attributes"] = attributes
        get_ledger().emit({"event_name": self.event_name, "kind": self.kind, "phase": "started", "trace": trace, "execution": execution, "runtime": runtime, "attributes": attributes, **{k:v for k,v in self.metadata.items() if k not in {"attributes"}}, **provenance})
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, tb: Any) -> bool:
        import time
        assert self.context is not None
        duration = (time.monotonic() - self.started) * 1000 if self.started else None
        phase = "failed" if exc else "completed"
        error = {} if exc is None else {"type": type(exc).__name__, "message": str(exc)[:2000]}
        get_ledger().emit({"event_name": self.event_name, "kind": self.kind, "phase": phase, "severity": "ERROR" if exc else "INFO", "trace": self.context["trace"], "execution": self.context["execution"], "runtime": self.context["runtime"], "outcome": {"status": "error" if exc else "ok"}, "duration_ms": duration, "error": error, "attributes": self.context.get("attributes", {}), **{k:v for k,v in self.context.items() if k not in {"trace", "execution", "runtime", "attributes"}}})
        if self.token is not None: _context.reset(self.token)
        return False

    async def __aenter__(self) -> "_Scope": return self.__enter__()
    async def __aexit__(self, exc_type: Any, exc: BaseException | None, tb: Any) -> bool: return self.__exit__(exc_type, exc, tb)


def operation(event_name: str, **metadata: Any) -> _Scope:
    return _Scope(event_name, kind="operation", **metadata)


def action(event_name: str, *, effect: str = "execute", scope: str = "local", **metadata: Any) -> _Scope:
    return _Scope(event_name, kind="action", effect=effect, scope=scope, **metadata)


def resource_action(resource: str, resource_id: str, *, effect: str = "read", scope: str = "local", **metadata: Any) -> _Scope:
    """Create a consistently shaped action for a concrete resource boundary."""
    safe = resource.strip().lower().replace("/", ".")
    return action(f"pap.{safe}.{effect}", effect=effect, scope=scope,
                  subject={"type": resource, "id": resource_id}, **metadata)


def filesystem(path: str | os.PathLike[str], *, effect: str = "read", **metadata: Any) -> _Scope:
    return resource_action("filesystem", str(path), effect=effect, **metadata)


def database(database_id: str, *, effect: str = "read", **metadata: Any) -> _Scope:
    return resource_action("database", database_id, effect=effect, **metadata)


def http(url: str, *, effect: str = "execute", **metadata: Any) -> _Scope:
    """Record a concrete HTTP request with a stable request semantic name."""
    return action("pap.http.request", effect=effect, scope="external",
                  subject={"type": "http", "id": url}, **metadata)


def tool(tool_id: str, *, effect: str = "execute", scope: str = "local", **metadata: Any) -> _Scope:
    return resource_action("tool", tool_id, effect=effect, scope=scope, **metadata)


def git(operation_name: str, repository: str = ".", *, effect: str = "execute", **metadata: Any) -> _Scope:
    return action(f"pap.git.{operation_name}", effect=effect, scope="local",
                  subject={"type": "git_repository", "id": repository}, **metadata)
