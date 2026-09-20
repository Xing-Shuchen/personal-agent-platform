from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from paplog import observe
from paplog.cli import main as paplog_main
from paplog.core import Ledger, redact
from pap.run import _queue_timing, _run_process, invoke
from pap.spec import load_spec


def _world_feeds_module():
    path = Path(__file__).resolve().parents[1] / "agents/world-historian/runtime/feeds.py"
    spec = importlib.util.spec_from_file_location("paplog_test_world_feeds", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nested_lifecycle_and_lineage(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    with observe.operation("pap.job.run", job={"id": "world-historian/news-follow"}):
        with observe.action("pap.model.call", effect="execute", scope="external"):
            observe.event("pap.artifact.created", subject={"type": "event_card", "id": "card-1"}, links=[{"type": "derived_from", "target_type": "artifact", "target_id": "source-1"}])
    ledger = observe.get_ledger()
    events = ledger.query()
    assert [item["phase"] for item in events if item["kind"] == "operation"] == ["started", "completed"]
    assert ledger.lineage("card-1")[0]["target_id"] == "source-1"


def test_action_keeps_parent_operation_identity_and_has_distinct_action_id(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    with observe.operation("pap.parent"):
        parent_operation = observe.current()["execution"]["operation_id"]
        with observe.action("pap.tool.call"):
            current = observe.current()["execution"]
            assert current["operation_id"] == parent_operation
            assert current["action_id"] != parent_operation


def test_resource_action_helpers_use_effect_and_scope(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    with observe.filesystem(tmp_path / "note.md", effect="write"):
        pass
    event = observe.get_ledger().query(event="pap.filesystem.write")[0]
    assert event["attributes"]["action.effect"] == "write"
    assert event["attributes"]["action.scope"] == "local"
    assert event["subject"]["type"] == "filesystem"
    terminal = observe.get_ledger().query(event="pap.filesystem.write")[-1]
    assert terminal["phase"] == "completed"
    assert terminal["attributes"]["action.effect"] == "write"


def test_world_feeds_runtime_emits_safe_http_and_database_actions(tmp_path: Path, monkeypatch) -> None:
    feeds = _world_feeds_module()
    observe.configure(tmp_path / "ledger")
    monkeypatch.setenv("PAP_OBSERVABILITY_DIR", str(tmp_path / "ledger"))
    monkeypatch.setenv("PAP_RUN_ID", "01KFEEDS0000000000000000000")

    class Response:
        def read(self): return b"<rss><channel/></rss>"
        def __enter__(self): return self
        def __exit__(self, *_args): return False

    monkeypatch.setattr(feeds.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    assert feeds.fetch_feed("https://example.test/rss?api_key=do-not-log") == "<rss><channel/></rss>"
    http = observe.get_ledger().query(event="pap.http.request")[-1]
    assert http["subject"]["id"] == "https://example.test/rss"

    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE sources (id TEXT PRIMARY KEY)")
    # The database action wraps the semantic write boundary; this minimal
    # schema intentionally makes the insert fail only after the action starts.
    try:
        feeds.ingest_feed(connection, feed_name="test", feed_url="https://example.test/rss",
                          fetch=lambda _: "<rss><channel/></rss>")
    except sqlite3.OperationalError:
        pass
    assert observe.get_ledger().query(event="pap.database.write")


def test_operation_context_has_node_id_before_child_propagation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PAP_NODE_ID", "test-node")
    observe.configure(tmp_path)
    with observe.operation("pap.test.node"):
        assert observe.current()["execution"]["node_id"] == "test-node"


def test_direct_child_event_inherits_pap_environment_context(tmp_path: Path, monkeypatch) -> None:
    observe.configure(tmp_path / "ledger")
    monkeypatch.setenv("TRACEPARENT", "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01")
    monkeypatch.setenv("PAP_RUN_ID", "01KCHILD0000000000000000000")
    monkeypatch.setenv("PAP_PARENT_OPERATION_ID", "01KCHILD0000000000000000001")
    monkeypatch.setenv("PAP_AGENT", "world-historian")
    monkeypatch.setenv("PAP_SKILL", "news-feeds")
    monkeypatch.setenv("PAP_JOB_ID", "world-historian/world-feeds")
    monkeypatch.setenv("PAP_NODE_ID", "test-node")
    event = observe.event("pap.artifact.created", subject={"type": "source_bundle", "id": "art_test"})
    assert event["trace"]["trace_id"] == "0123456789abcdef0123456789abcdef"
    assert event["trace"]["parent_span_id"] == "0123456789abcdef"
    assert event["execution"] == {
        "run_id": "01KCHILD0000000000000000000",
        "operation_id": "01KCHILD0000000000000000001",
        "node_id": "test-node",
    }
    assert event["agent"] == {"id": "world-historian"}
    assert event["skill"] == {"id": "news-feeds"}
    assert event["job"] == {"id": "world-historian/world-feeds"}


def test_paplog_exec_propagates_node_id_to_actual_child(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PAP_NODE_ID", "child-node")
    output = tmp_path / "node.txt"
    assert paplog_main(["--directory", str(tmp_path / "ledger"), "exec", "--", sys.executable, "-c",
                        "import os, pathlib, sys; pathlib.Path(sys.argv[1]).write_text(os.environ['PAP_NODE_ID'])", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == "child-node"


def test_paplog_exec_records_operation_and_process_action(tmp_path: Path) -> None:
    assert paplog_main(["--directory", str(tmp_path / "ledger"), "exec", "--", sys.executable, "-c", "pass"]) == 0
    events = Ledger(tmp_path / "ledger").query()
    assert any(event["event_name"] == "pap.exec" and event["kind"] == "operation" for event in events)
    assert [event["phase"] for event in events if event["event_name"] == "pap.process.exec"] == ["started", "completed"]


def test_paplog_exec_child_domain_event_uses_the_parent_ledger(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger"
    code = (
        "from paplog import observe; "
        "observe.event('pap.artifact.created', subject={'type':'brief','id':'art_child'})"
    )
    assert paplog_main(["--directory", str(ledger_path), "exec", "--job", "test/child", "--",
                        sys.executable, "-c", code]) == 0
    events = Ledger(ledger_path).query(event="pap.artifact.created")
    assert len(events) == 1
    parent = Ledger(ledger_path).query(event="pap.exec")[0]
    assert events[0]["execution"]["run_id"] == parent["execution"]["run_id"]
    assert events[0]["execution"]["operation_id"] == parent["execution"]["operation_id"]
    assert events[0]["job"] == {"id": "test/child"}


def test_paplog_exec_failure_is_queryable_without_spool_reconciliation(tmp_path: Path) -> None:
    code = "import sys; sys.exit(7)"
    assert paplog_main(["--directory", str(tmp_path / "ledger"), "exec", "--", sys.executable, "-c", code]) == 7
    ledger = Ledger(tmp_path / "ledger")
    failed = [event for event in ledger.query() if event["phase"] == "failed"]
    assert {event["event_name"] for event in failed} == {"pap.exec", "pap.process.exec"}
    assert not list(ledger.spool.glob("*.json"))


def test_lineage_traverses_upstream_and_downstream_without_cycles(tmp_path: Path, capsys) -> None:
    ledger = Ledger(tmp_path)
    for source, target in (("brief", "card"), ("card", "source"), ("card", "brief")):
        ledger.emit({"event_name": "pap.artifact.created", "subject": {"type": "artifact", "id": source},
                     "links": [{"type": "derived_from", "target_type": "artifact", "target_id": target}]})
    links = ledger.lineage("brief", depth=4)
    assert {(link["source_id"], link["target_id"]) for link in links} == {
        ("brief", "card"), ("card", "source"), ("card", "brief")}
    assert max(link["depth"] for link in links) <= 2
    assert paplog_main(["--directory", str(tmp_path), "lineage", "brief", "--depth", "2"]) == 0
    output = capsys.readouterr().out
    assert "card → derived_from → artifact:source" in output


def test_redaction_and_spool_reconcile(tmp_path: Path) -> None:
    assert redact({"Authorization": "Bearer abc.def.ghi", "input_tokens": 7, "nested": {"api_key": "secret"}}) == {"Authorization": "[REDACTED]", "input_tokens": 7, "nested": {"api_key": "[REDACTED]"}}
    ledger = Ledger(tmp_path)
    record = ledger.emit({"event_name": "pap.test"})
    ledger._spool(record)
    assert ledger.reconcile() == (1, 0)
    assert ledger.query(event="pap.test")


def test_redaction_removes_inline_secrets_from_errors_and_environment_strings(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    event = ledger.emit({"event_name": "pap.test.redaction", "error": {"message": "request failed: api_key=top-secret"},
                         "attributes": {"environment": ["TOKEN=also-secret", "LANG=C"]}})
    assert event["error"]["message"] == "[REDACTED]"
    assert event["attributes"]["environment"] == ["[REDACTED]", "LANG=C"]
    assert "secret" not in json.dumps(ledger.query(event="pap.test.redaction"), ensure_ascii=False).lower()


def test_content_policy_covers_provider_and_historian_body_aliases(tmp_path: Path) -> None:
    event = Ledger(tmp_path).emit({"event_name": "pap.test.content_aliases", "attributes": {
        "prompt_text": "private prompt", "source_text": "historian source", "request_body": "http body"
    }})
    for key in ("prompt_text", "source_text", "request_body"):
        assert event["attributes"][key]["bytes"] > 0
        assert "private" not in json.dumps(event["attributes"][key])


def test_sqlite_write_failure_spools_and_does_not_raise(tmp_path: Path, monkeypatch) -> None:
    ledger = Ledger(tmp_path)
    monkeypatch.setattr(ledger, "_persist", lambda _: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    event = ledger.emit({"event_name": "pap.test.fail_open"})
    assert event["event_name"] == "pap.test.fail_open"
    spooled = list(ledger.spool.glob("*.json"))
    assert len(spooled) == 1
    assert json.loads(spooled[0].read_text(encoding="utf-8"))["event_id"] == event["event_id"]
    mirror = list((tmp_path / "jsonl").glob("*.jsonl"))
    assert len(mirror) == 1
    assert json.loads(mirror[0].read_text(encoding="utf-8").splitlines()[-1])["event_id"] == event["event_id"]
    monkeypatch.undo()
    assert ledger.reconcile() == (1, 0)
    assert len(mirror[0].read_text(encoding="utf-8").splitlines()) == 1


def test_reconcile_reapplies_redaction_to_legacy_or_tampered_spool(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    event = ledger.emit({"event_name": "pap.test.reconcile"})
    ledger._spool({**event, "event_id": "legacy-spool-id", "attributes": {"message": "private body", "Authorization": "Bearer secret.token"}})
    assert ledger.reconcile() == (1, 0)
    restored = ledger.query(event="pap.test.reconcile")
    assert all("private body" not in json.dumps(item, ensure_ascii=False) for item in restored)
    assert re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", restored[-1]["event_id"])
    assert restored[-1]["attributes"] == {"message": {"sha256": "sha256:" + __import__("hashlib").sha256(b"private body").hexdigest(), "bytes": 12}, "Authorization": "[REDACTED]"}


def test_reconcile_accepts_minimal_legacy_spool_records(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.spool.mkdir(parents=True)
    path = ledger.spool / "legacy.json"
    path.write_text(json.dumps({"event_name": "pap.legacy.event", "attributes": {"body": "private"}}), encoding="utf-8")
    assert ledger.reconcile() == (1, 0)
    restored = ledger.query(event="pap.legacy.event")[0]
    assert restored["attributes"]["body"]["bytes"] == len("private".encode())


def test_async_context_is_isolated(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    async def work(name: str) -> None:
        async with observe.operation("pap.skill.run", skill={"id": name}):
            await asyncio.sleep(0)
            observe.event("pap.test.async")
    async def both() -> None:
        await asyncio.gather(work("a"), work("b"))
    asyncio.run(both())
    events = observe.get_ledger().query(event="pap.test.async")
    assert {event["skill"]["id"] for event in events} == {"a", "b"}


def test_scheduler_projection_detects_frequency_inversion(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    for job, klass, stamps in (("high", "high", (0, 100)), ("normal", "normal", (0, 10))):
        for stamp in stamps:
            ledger.emit({"event_name": "pap.schedule.dispatched", "timestamp": f"2026-01-01T00:{stamp:02d}:00+00:00" if stamp < 60 else "2026-01-01T01:40:00+00:00", "observed_timestamp": "2026-01-01T00:00:00+00:00", "job": {"id": job}, "attributes": {"tracking_class": klass}})
    health = ledger.scheduler_health()
    assert health["observed_cadence_s"]["high"] > health["observed_cadence_s"]["normal"]
    assert health["frequency_inversions"][0]["higher_class"] == "high"


def test_scheduler_projection_reports_late_and_queue_timing(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.emit({"event_name": "pap.schedule.due", "attributes": {"schedule_lag_ms": 50}})
    ledger.emit({"event_name": "pap.run.started", "attributes": {"queue_delay_ms": 20}})
    health = ledger.scheduler_health()
    assert health["late_runs"] == 1
    assert health["median_queue_delay_ms"] == 20


def test_scheduler_projection_counts_nested_abandonment_once_per_run(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    for operation in ("run", "agent", "skill"):
        ledger.emit({"event_name": "pap.operation.abandoned", "kind": "operation", "phase": "abandoned",
                     "execution": {"run_id": "run-1", "operation_id": operation}})
    assert ledger.scheduler_health()["abandoned_runs"] == 1


def test_process_action_records_nonzero_exit_without_output(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    result = _run_process(lambda command, **_: subprocess.CompletedProcess(command, 7, "secret stdout", "secret stderr"), ["example", "--secret"])
    assert result.returncode == 7
    event = observe.get_ledger().query(event="pap.process.exec")[-1]
    assert event["phase"] == "failed"
    assert event["attributes"]["exit_code"] == 7
    assert "stdout" not in event["attributes"]


def test_process_action_records_termination_signal(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    _run_process(lambda command, **_: subprocess.CompletedProcess(command, -15, "", ""), ["example"])
    event = observe.get_ledger().query(event="pap.process.exec")[-1]
    assert event["attributes"]["termination_signal"] == 15


def test_process_action_is_a_child_span_with_one_action_id(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    parent = {"trace_id": "a" * 32, "span_id": "b" * 16}
    _run_process(lambda command, **_: subprocess.CompletedProcess(command, 0, "", ""), ["example"],
                 trace=parent, execution={"run_id": "run-1", "operation_id": "op-1"})
    events = observe.get_ledger().query(event="pap.process.exec")
    assert len(events) == 2
    assert {event["execution"]["action_id"] for event in events} == {events[0]["execution"]["action_id"]}
    assert {event["trace"]["parent_span_id"] for event in events} == {parent["span_id"]}
    assert {event["trace"]["span_id"] for event in events} != {parent["span_id"]}


def test_rebuildable_run_and_model_projections(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    shared = {"execution": {"run_id": "run-1"}, "job": {"id": "compiler-news/daily"}, "agent": {"id": "compiler-news"}, "skill": {"id": "compiler-hpc-brief"}}
    ledger.emit({"event_name": "pap.run.started", **shared})
    ledger.emit({"event_name": "pap.model.call", **shared, "attributes": {"provider": "deepseek", "requested_model": "v4", "input_tokens": 12, "output_tokens": 3, "cost.amount": 0.1, "cost.currency": "CNY", "cost.source": "provider-reported"}})
    ledger.emit({"event_name": "pap.run.completed", **shared, "outcome": {"status": "ok"}})
    assert ledger.rebuild_index() == 3
    with ledger._connect() as con:
        assert con.execute("SELECT outcome FROM runs WHERE run_id='run-1'").fetchone()[0] == "ok"
        assert con.execute("SELECT input_tokens FROM model_usage").fetchone()[0] == 12


def test_model_latency_is_projected_from_usage_attributes(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.emit({"event_name": "pap.model.call", "attributes": {
        "provider": "acme", "requested_model": "m", "input_tokens": 1,
        "output_tokens": 1, "latency_ms": 42.5
    }})
    ledger.rebuild_index()
    with ledger._connect() as con:
        assert con.execute("SELECT latency_ms FROM model_usage").fetchone()[0] == 42.5


def test_model_usage_projection_keeps_token_breakdowns_and_price_version(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.emit({"event_name": "pap.model.call", "attributes": {
        "provider": "acme", "requested_model": "m", "input_tokens": 1,
        "output_tokens": 1, "cache_read_tokens": 2, "cache_write_tokens": 3,
        "reasoning_tokens": 4, "pricing_version": "p-v1"
    }})
    ledger.rebuild_index()
    with ledger._connect() as con:
        row = con.execute("SELECT cache_read_tokens,cache_write_tokens,reasoning_tokens,pricing_version FROM model_usage").fetchone()
    assert tuple(row) == (2, 3, 4, "p-v1")


def test_rebuildable_operation_and_action_projections(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    observe.configure(tmp_path)
    with observe.operation("pap.test.operation"):
        with observe.action("pap.tool.call", effect="execute"):
            pass
    assert ledger.rebuild_index() > 0
    with ledger._connect() as con:
        assert con.execute("SELECT count(*) FROM operations").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM actions").fetchone()[0] == 1
        assert con.execute("SELECT outcome FROM actions").fetchone()[0] == "ok"


def test_versioned_price_table_estimates_missing_provider_cost(tmp_path: Path, monkeypatch) -> None:
    pricing = tmp_path / "pricing.json"
    pricing.write_text(json.dumps({"version": "prices-2026-09", "models": {
        "acme/model": {"input_per_million": 2.0, "output_per_million": 4.0, "currency": "USD"}
    }}), encoding="utf-8")
    monkeypatch.setenv("PAPLOG_PRICING_JSON", str(pricing))
    event = Ledger(tmp_path / "ledger").emit({"event_name": "pap.model.call", "attributes": {
        "provider": "acme", "returned_model": "model", "input_tokens": 1000, "output_tokens": 500
    }})
    assert event["attributes"]["cost.amount"] == 0.004
    assert event["attributes"]["cost.source"] == "estimated"
    assert event["attributes"]["cost.pricing_version"] == "prices-2026-09"


def test_invalid_supplied_event_id_is_replaced_with_a_ulid(tmp_path: Path) -> None:
    event = Ledger(tmp_path).emit({"event_name": "pap.test.id", "event_id": "legacy-id"})
    assert re.fullmatch(r"[0-9A-HJKMNP-TV-Z]{26}", event["event_id"])


def test_ledger_emission_pins_canonical_schema_version(tmp_path: Path) -> None:
    event = Ledger(tmp_path).emit({"event_name": "pap.test.schema", "schema": "pap.event.v1"})
    assert event["schema"] == "pap.event.v2"


def test_invalid_event_name_becomes_a_metadata_only_diagnostic(tmp_path: Path) -> None:
    event = Ledger(tmp_path).emit({"event_name": "Bad Name", "attributes": {"body": "not retained"}})
    assert event["event_name"] == "paplog.invalid_event"
    assert "Bad Name" not in json.dumps(event, ensure_ascii=False)
    assert event["attributes"]["rejected_event_name"]["bytes"] == len("Bad Name".encode())


def test_malformed_structured_fields_are_fail_open_normalized(tmp_path: Path) -> None:
    event = Ledger(tmp_path).emit({"event_name": "pap.test.malformed", "trace": None,
                                   "execution": None, "job": None, "subject": None,
                                   "outcome": None, "error": None, "links": None})
    assert event["event_name"] == "pap.test.malformed"
    assert event["execution"]["node_id"]
    assert Ledger(tmp_path).query(event="pap.test.malformed")


def test_concurrent_writers_preserve_all_unique_events(tmp_path: Path) -> None:
    def write(index: int) -> None:
        Ledger(tmp_path).emit({"event_name": "pap.test.concurrent", "attributes": {"index": index}})
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(32)))
    assert len(Ledger(tmp_path).query(event="pap.test.concurrent")) == 32


def test_stale_started_operation_becomes_separate_abandoned_event(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path)
    ledger.emit({"event_name": "pap.job.run", "kind": "operation", "phase": "started", "timestamp": "2000-01-01T00:00:00+00:00", "observed_timestamp": "2000-01-01T00:00:00+00:00", "execution": {"run_id": "run-old", "operation_id": "op-old"}})
    assert ledger.abandon_stale(1) == 1
    events = ledger.query(run="run-old")
    assert [event["phase"] for event in events] == ["started", "abandoned"]


def test_point_event_gets_trace_and_preserves_explicit_action_kind(tmp_path: Path) -> None:
    observe.configure(tmp_path)
    observe.event("pap.message.send", kind="action", phase="started", execution={"run_id": "run-1"})
    event = observe.get_ledger().query()[0]
    assert event["kind"] == "action"
    assert len(event["trace"]["trace_id"]) == 32
    assert len(event["trace"]["span_id"]) == 16


def test_scheduled_run_queue_delay_is_measured_from_dispatch_not_due() -> None:
    started = __import__("datetime").datetime.fromisoformat("2026-01-01T00:00:12+00:00")
    timing = _queue_timing({"type": "schedule", "scheduled_for": "2026-01-01T00:00:00+00:00",
                            "dispatched_at": "2026-01-01T00:00:10+00:00"}, started)
    assert timing == {"scheduled_for": "2026-01-01T00:00:00+00:00",
                      "dispatched_at": "2026-01-01T00:00:10+00:00", "queue_delay_ms": 2000.0}


def test_run_records_nested_agent_skill_and_process_operations(tmp_path: Path, capsys) -> None:
    skill_dir = tmp_path / "agents/sample/profile/skills/example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "agents/sample/agent.yaml").write_text("""apiVersion: pap/v1
kind: Agent
metadata: {name: sample, description: sample}
spec:
  profile: {name: sample, source: profile}
""", encoding="utf-8")
    observe.configure(tmp_path / "ledger")
    result = invoke(root=tmp_path, spec=load_spec(tmp_path / "agents/sample/agent.yaml"), skill="example",
                    runner_backend="command", command=["tool"], run_log=tmp_path / "runs.jsonl",
                    command_runner=lambda command, **_: subprocess.CompletedProcess(command, 0, "", ""))
    events = observe.get_ledger().query(run=result.run_id)
    assert all(event["agent"].get("definition_version", "").startswith("sha256:") for event in events if event.get("agent"))
    starts = {item["event_name"]: item for item in events if item["phase"] == "started"}
    assert {"pap.run.started", "pap.agent.invoke", "pap.skill.invoke", "pap.process.exec"} <= starts.keys()
    assert starts["pap.agent.invoke"]["trace"]["parent_span_id"] == starts["pap.run.started"]["trace"]["span_id"]
    assert starts["pap.skill.invoke"]["trace"]["parent_span_id"] == starts["pap.agent.invoke"]["trace"]["span_id"]
    assert starts["pap.process.exec"]["trace"]["parent_span_id"] == starts["pap.skill.invoke"]["trace"]["span_id"]
    assert paplog_main(["--directory", str(tmp_path / "ledger"), "run", result.run_id]) == 0
    tree = capsys.readouterr().out
    assert tree.index("pap.run.started") < tree.index("pap.agent.invoke") < tree.index("pap.skill.invoke") < tree.index("pap.process.exec")


def test_jobs_cli_aggregates_canonical_lifecycle_events(tmp_path: Path, capsys) -> None:
    ledger = Ledger(tmp_path)
    shared = {"job": {"id": "sample/daily"}, "execution": {"run_id": "run-1"}}
    ledger.emit({"event_name": "pap.schedule.due", **shared, "attributes": {"scheduled_for": "2026-01-01T00:00:00+00:00"}})
    ledger.emit({"event_name": "pap.schedule.dispatched", **shared, "attributes": {"dispatched_at": "2026-01-01T00:00:01+00:00"}})
    ledger.emit({"event_name": "pap.run.started", **shared, "attributes": {"started_at": "2026-01-01T00:00:02+00:00"}})
    ledger.emit({"event_name": "pap.run.completed", **shared, "outcome": {"status": "ok"}})
    assert paplog_main(["--directory", str(tmp_path), "jobs", "--json"]) == 0
    row = json.loads(capsys.readouterr().out)[0]
    assert {key: row[key] for key in ("job_id", "due", "dispatched", "started", "completed", "failed", "abandoned", "last_outcome")} == {
        "job_id": "sample/daily", "due": 1, "dispatched": 1, "started": 1,
        "completed": 1, "failed": 0, "abandoned": 0, "last_outcome": "ok"}
    assert row["last_scheduled_for"] == "2026-01-01T00:00:00+00:00"
    assert row["last_dispatched_at"] == "2026-01-01T00:00:01+00:00"
    assert row["last_started_at"] == "2026-01-01T00:00:02+00:00"
    assert row["last_completed_at"]


def test_artifacts_cli_includes_pap_and_historian_durable_artifacts(tmp_path: Path, capsys) -> None:
    ledger = Ledger(tmp_path)
    ledger.emit({"event_name": "pap.artifact.created", "subject": {"type": "brief", "id": "pap-1"}})
    ledger.emit({"event_name": "historian.artifact.created", "subject": {"type": "event-card", "id": "hist-1"}})
    ledger.emit({"event_name": "historian.context_pack.created", "subject": {"type": "context", "id": "pack-1"}})
    ledger.emit({"event_name": "historian.event_revision.created", "subject": {"type": "event", "id": "revision-1"}})
    ledger.emit({"event_name": "pap.model.call"})
    assert paplog_main(["--directory", str(tmp_path), "artifacts", "--json"]) == 0
    assert {row["event_name"] for row in json.loads(capsys.readouterr().out)} == {
        "pap.artifact.created", "historian.artifact.created", "historian.context_pack.created", "historian.event_revision.created"}


def test_models_cli_aggregates_usage_and_cost(tmp_path: Path, capsys) -> None:
    ledger = Ledger(tmp_path)
    shared = {"event_name": "pap.model.call", "attributes": {"provider": "deepseek", "requested_model": "deepseek/v4", "input_tokens": 10, "output_tokens": 4, "cost.amount": 0.2, "fallback_count": 1}}
    ledger.emit(shared)
    ledger.emit({**shared, "attributes": {**shared["attributes"], "input_tokens": 3, "cost.amount": None}})
    assert paplog_main(["--directory", str(tmp_path), "models", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [{"provider": "deepseek", "model": "deepseek/v4", "calls": 2, "input_tokens": 13, "output_tokens": 8, "cost": 0.2, "unknown_cost": 1, "fallback_calls": 2}]


def test_failures_cli_supports_run_filter(tmp_path: Path, capsys) -> None:
    ledger = Ledger(tmp_path)
    ledger.emit({"event_name": "pap.run.failed", "execution": {"run_id": "run-bad"}, "outcome": {"status": "error"}})
    ledger.emit({"event_name": "pap.run.failed", "execution": {"run_id": "run-good"}, "outcome": {"status": "error"}})
    assert paplog_main(["--directory", str(tmp_path), "failures", "--run", "run-bad", "--json"]) == 0
    assert [row["execution"]["run_id"] for row in json.loads(capsys.readouterr().out)] == ["run-bad"]


def test_tail_cli_prints_a_snapshot(tmp_path: Path, capsys) -> None:
    Ledger(tmp_path).emit({"event_name": "pap.test.tail"})
    assert paplog_main(["--directory", str(tmp_path), "tail", "--event", "pap.test.tail"]) == 0
    assert "pap.test.tail" in capsys.readouterr().out
