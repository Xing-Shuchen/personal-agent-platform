from __future__ import annotations

import json
import threading
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from agents.librarian.runtime import bookscan_review_server as review_server
from agents.librarian.runtime.bookscan_review_server import create_server


def test_local_review_requires_bootstrap_cookie_and_same_origin(tmp_path):
    server, url = create_server(tmp_path, "owner", None, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        try:
            urlopen(origin + "/review/index.html")
            assert False, "unauthorized review page was served"
        except HTTPError as error:
            assert error.code == 403
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        assert b"Bookscan" in opener.open(url).read()
        assert "手写笔记复核" in opener.open(url + "&view=handwriting").read().decode()
        try:
            opener.open(origin + "/bookscan-runs/%2e%2e/review/index.html")
            assert False, "path traversal was served"
        except HTTPError as error:
            assert error.code == 404
        body = json.dumps({"run_id": "unknown", "pages": {}}).encode()
        request = Request(origin + "/api/review", data=body,
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            opener.open(request)
            assert False, "cross-origin form was accepted"
        except HTTPError as error:
            assert error.code == 403
        request.add_header("Origin", origin)
        try:
            opener.open(request)
            assert False, "unknown review run was accepted"
        except HTTPError as error:
            assert error.code == 400
            assert json.loads(error.read())["code"] == "VALIDATION_FAILED"
        handwriting = Request(origin + "/api/handwriting-review", data=b"{}",
                              headers={"Content-Type": "application/json"}, method="POST")
        try:
            opener.open(handwriting)
            assert False, "cross-origin handwriting review was accepted"
        except HTTPError as error:
            assert error.code == 403
        handwriting.add_header("Origin", origin)
        try:
            opener.open(handwriting)
            assert False, "empty handwriting review was accepted"
        except HTTPError as error:
            assert error.code == 400
            assert json.loads(error.read())["code"] == "VALIDATION_FAILED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_committed_handwriting_decision_reports_review_page_failure(tmp_path, monkeypatch):
    server, url = create_server(tmp_path, "owner", None, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    decisions = []
    monkeypatch.setattr(review_server, "review_handwriting", lambda _lib, _owner, bundle:
                        decisions.append(bundle) or {"status": "applied", "trace_id": "trace_one",
                                                      "revision": 2})
    monkeypatch.setattr(review_server, "build_index", lambda *_: (_ for _ in ()).throw(
        OSError("private review path unavailable")))
    monkeypatch.setattr(review_server, "run_worker", lambda *_args, **_kwargs: [])
    try:
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        opener.open(url).read()
        body = json.dumps({"trace_id": "trace_one", "expected_revision": 1,
                           "decision": "accepted", "text": "Reviewed"}).encode()
        request = Request(origin + "/api/handwriting-review", data=body,
                          headers={"Content-Type": "application/json", "Origin": origin},
                          method="POST")
        with opener.open(request) as response:
            result = json.loads(response.read())
        assert result == {"status": "applied", "trace_id": "trace_one", "revision": 2,
                          "vault_status": "unconfigured", "review_page_status": "review_required"}
        assert len(decisions) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
