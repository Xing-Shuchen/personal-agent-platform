"""Tests for append-only artifacts."""

import json

import pytest

from pap.artifact import ArtifactError, append, artifacts, new_artifact_id


def test_append_is_append_only_and_ids_stable(tmp_path):
    log = tmp_path / "artifacts.jsonl"
    first = append("news.thread.created", "world-historian",
                   {"thread_id": "thr_1"}, provenance={"run_id": "run_x"},
                   log_path=log)
    second = append("news.relation.discovered", "world-historian",
                    {"relation_id": "rel_1"}, log_path=log)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert records[0]["id"] == first.id
    assert records[0]["payload"] == {"thread_id": "thr_1"}
    assert records[0]["provenance"] == {"run_id": "run_x"}
    assert records[1]["type"] == "news.relation.discovered"
    # appending never rewrites earlier lines
    assert records[0] == json.loads(lines[0])


def test_artifacts_filter_by_type_and_producer(tmp_path):
    log = tmp_path / "artifacts.jsonl"
    append("news.thread.created", "world-historian", {}, log_path=log)
    append("news.report.generated", "world-historian", {}, log_path=log)
    append("intel.brief", "intelligence", {}, log_path=log)
    assert len(artifacts(log)) == 3
    assert len(artifacts(log, artifact_type="news.thread.created")) == 1
    assert len(artifacts(log, producer="intelligence")) == 1
    assert len(artifacts(log, producer="serendipity")) == 0


def test_append_rejects_malformed_records(tmp_path):
    log = tmp_path / "artifacts.jsonl"
    with pytest.raises(ArtifactError):
        append("", "world-historian", {}, log_path=log)
    with pytest.raises(ArtifactError):
        append("news.thread.created", "", {}, log_path=log)
    with pytest.raises(ArtifactError):
        append("news.thread.created", "world-historian",
               ["not-an-object"], log_path=log)  # type: ignore[arg-type]
    with pytest.raises(ArtifactError):
        append("news.thread.created", "world-historian", {},
               provenance="run_x", log_path=log)  # type: ignore[arg-type]
    assert not log.exists()


def test_artifact_id_is_prefixed_and_unique():
    a = new_artifact_id("news.thread.created")
    b = new_artifact_id("news.thread.created")
    assert a.startswith("art_news_thread_created_")
    assert a != b
