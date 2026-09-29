from __future__ import annotations

import json
import threading
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

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
