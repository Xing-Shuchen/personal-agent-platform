"""Private localhost UI for applying complete Bookscan reviews."""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import secrets
import threading
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .bookscan_review_apply import MAX_BUNDLE_BYTES, apply_review, review_context
from .handwriting_review import review_handwriting
from .review_index import build_index
from .store import Library, LibrarianError
from .worker import run as run_worker


def create_server(root: Path, owner: str, vault: Path | None,
                  port: int = 8765) -> tuple[ThreadingHTTPServer, str]:
    root = root.resolve()
    build_index(root, owner)
    bootstrap = secrets.token_urlsafe(32)
    cookie_secret = secrets.token_urlsafe(32)
    apply_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def _host_ok(self) -> bool:
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def _authorized(self) -> bool:
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
            except Exception:
                return False
            item = cookie.get("librarian_review")
            return bool(item and hmac.compare_digest(item.value, cookie_secret))

        def _json(self, status: HTTPStatus, value: dict) -> None:
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if not self._host_ok():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            parsed = urlsplit(self.path)
            if parsed.path == "/" and hmac.compare_digest(
                    parse_qs(parsed.query).get("token", [""])[0], bootstrap):
                destination = ("/review/handwriting.html" if
                               parse_qs(parsed.query).get("view") == ["handwriting"] else
                               "/review/index.html")
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", destination)
                self.send_header("Set-Cookie", f"librarian_review={cookie_secret}; "
                                 "HttpOnly; SameSite=Strict; Path=/")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            if not self._authorized():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if parsed.path == "/api/review-context":
                run_id = parse_qs(parsed.query).get("run_id", [""])[0]
                try:
                    with Library(root) as lib:
                        self._json(HTTPStatus.OK, review_context(lib, owner, run_id))
                except LibrarianError as error:
                    self._json(HTTPStatus.BAD_REQUEST,
                               {"code": error.code, "message": str(error)})
                return
            relative = unquote(parsed.path).lstrip("/")
            if not (relative.startswith("review/") or
                    relative.startswith("bookscan-runs/")):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            target = (root / relative).resolve()
            allowed = ((root / "review") if relative.startswith("review/") else
                       (root / "bookscan-runs")).resolve()
            if not target.is_relative_to(allowed) or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            payload = target.read_bytes()
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime}; charset=utf-8" if mime == "text/html" else mime)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            if (not self._host_ok() or not self._authorized() or
                    self.headers.get("Origin") !=
                    f"http://127.0.0.1:{self.server.server_port}"):
                self._json(HTTPStatus.FORBIDDEN, {"code": "FORBIDDEN",
                                                  "message": "review session required"})
                return
            route = urlsplit(self.path).path
            if route not in {"/api/review", "/api/handwriting-review"}:
                self._json(HTTPStatus.NOT_FOUND, {"code": "NOT_FOUND"})
                return
            try:
                size = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                size = -1
            if size < 1 or size > MAX_BUNDLE_BYTES or \
                    self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                self._json(HTTPStatus.BAD_REQUEST, {"code": "VALIDATION_FAILED",
                                                    "message": "invalid review bundle size or type"})
                return
            try:
                bundle = json.loads(self.rfile.read(size))
                with apply_lock:
                    with Library(root) as lib:
                        result = (review_handwriting(lib, owner, bundle)
                                  if route == "/api/handwriting-review" else
                                  apply_review(lib, owner, bundle))
                    review_page_status = "unchanged"
                    if route == "/api/handwriting-review":
                        try:
                            build_index(root, owner)
                            review_page_status = "updated"
                        except Exception:
                            # The decision is committed; report a projection failure so
                            # a retry can rebuild the page without a second revision.
                            review_page_status = "review_required"
                    try:
                        worker = run_worker(root, vault, owner, physical_only=True)
                    except Exception:
                        worker = [{"status": "error", "source": "vault_note"}]
                if any(item.get("status") == "already_running" for item in worker):
                    vault_status = "awaiting_worker"
                elif any(item.get("source") == "vault_note" or
                         item.get("status") == "error" for item in worker):
                    vault_status = "review_required"
                else:
                    vault_status = "updated" if vault else "unconfigured"
                self._json(HTTPStatus.OK, {**result, "vault_status": vault_status,
                                           "review_page_status": review_page_status})
            except LibrarianError as error:
                status = (HTTPStatus.CONFLICT if error.code in
                          {"REVISION_CONFLICT", "RECONCILIATION_REQUIRED"} else
                          HTTPStatus.BAD_REQUEST)
                self._json(status, {"code": error.code, "message": str(error)})
            except (ValueError, TypeError, UnicodeDecodeError):
                self._json(HTTPStatus.BAD_REQUEST, {"code": "VALIDATION_FAILED",
                                                    "message": "invalid review JSON"})

        def log_message(self, format: str, *args: object) -> None:
            # The bootstrap URL carries a one-time secret in its query string.
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}/?token={bootstrap}"
    return server, url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server, url = create_server(args.root, args.owner, args.vault, args.port)
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
