"""Persistent OCR worker over a configured command, including SSH stdio.

Only lossless image crops and OCR results cross the transport. No listening
service, database sharing, or remote access to the source library is needed.
"""
from __future__ import annotations

import argparse
import atexit
import base64
import contextlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time

import cv2
import numpy as np

PREFIX = b"BOOKSCAN_RPC "


class RemoteOCR:
    def __init__(self, config: dict):
        models = config["models"]
        command = models["remote_command"]
        if not isinstance(command, list) or not command or not all(
                isinstance(arg, str) for arg in command):
            raise ValueError("models.remote_command must be a nonempty argument list")
        self.timeout = float(models.get("remote_timeout", 120))
        self.buffer = b""
        self.log = tempfile.TemporaryFile()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.log)
        atexit.register(self.close)
        try:
            ready = self._read()
            self.det_name = ready["detection_name"]
            self.rec_name = ready["recognition_name"]
            self.hashes = ready["hashes"]
        except BaseException:
            self.close()
            raise

    def close(self):
        atexit.unregister(self.close)
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
        self.process.stdout.close()
        self.log.close()

    def _read(self):
        deadline = time.monotonic() + self.timeout
        while True:
            if b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                if not line.startswith(PREFIX):
                    continue
                reply = json.loads(line[len(PREFIX):])
                if "error" in reply:
                    raise RuntimeError("remote OCR: " + reply["error"])
                return reply
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select(
                    [self.process.stdout], [], [], max(0, remaining))[0]:
                raise TimeoutError("remote OCR response timed out")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                self.log.seek(0, 2)
                self.log.seek(max(0, self.log.tell() - 2000))
                raise RuntimeError("remote OCR worker exited: " +
                                   self.log.read().decode(errors="replace"))
            self.buffer += chunk

    def _request(self, operation, image):
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            raise ValueError("cannot encode OCR input")
        request = {"operation": operation,
                   "image": base64.b64encode(encoded).decode("ascii")}
        try:
            self.process.stdin.write(json.dumps(request).encode() + b"\n")
            self.process.stdin.flush()
            return self._read()["result"]
        except BaseException:
            self.close()
            raise

    def detect(self, image):
        return self._request("detect", image)

    def recognize(self, image):
        if image.size == 0:
            return "", None
        return tuple(self._request("recognize", image))


def serve(config):
    # Keep Python library logs off the protocol stream.
    output = sys.stdout

    def send(value):
        output.write(PREFIX.decode() + json.dumps(value, ensure_ascii=False) + "\n")
        output.flush()

    try:
        with contextlib.redirect_stdout(sys.stderr):
            from .vision import OCR
            if config["models"].get("remote_command"):
                raise ValueError("worker config must select local models")
            ocr = OCR(config)
        send({"detection_name": ocr.det_name, "recognition_name": ocr.rec_name,
              "hashes": ocr.hashes})
        for line in sys.stdin:
            request = json.loads(line)
            image = cv2.imdecode(np.frombuffer(base64.b64decode(request["image"]),
                                               dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("invalid OCR image")
            operation = request["operation"]
            if operation not in {"detect", "recognize"}:
                raise ValueError("unknown OCR operation")
            with contextlib.redirect_stdout(sys.stderr):
                result = getattr(ocr, operation)(image)
            send({"result": result})
    except Exception as exc:
        send({"error": str(exc)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["HF_HUB_OFFLINE"] = "1"
    import yaml
    serve(yaml.safe_load(args.config.read_text()))
