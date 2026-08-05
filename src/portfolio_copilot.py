"""Serve the portfolio UI and relay model deltas as server-sent events."""

from __future__ import annotations

import json
import logging
import os
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fintech_stream import FintechStreamClient


HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8080"))
INDEX_HTML = Path(__file__).parents[1] / "static" / "index.html"
PORTFOLIO_CONTEXT = "Cash: $18,400; Treasury ETF: $31,600; Equity ETF: $50,000"
LOG = logging.getLogger("portfolio_copilot")


def encode_sse(event: str, payload: dict[str, object]) -> bytes:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")


class PortfolioHandler(BaseHTTPRequestHandler):
    stream_client: FintechStreamClient

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = INDEX_HTML.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path != "/stream":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        request_id = self.headers.get("Idempotency-Key") or str(uuid.uuid4())
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            prompt = str(body["prompt"]).strip()
            if not prompt:
                raise ValueError("prompt is empty")

            # Acquire the upstream iterator before committing downstream headers.
            chunks = self.stream_client.stream_briefing(
                prompt=prompt,
                portfolio_context=PORTFOLIO_CONTEXT,
                request_id=request_id,
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception:
            LOG.exception("request_id=%s upstream request failed", request_id)
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {"error": "The briefing could not be started", "request_id": request_id},
            )
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("X-Request-Id", request_id)
        self.end_headers()

        try:
            self.wfile.write(encode_sse("ready", {"request_id": request_id}))
            self.wfile.flush()
            for chunk in chunks:
                text = chunk.choices[0].delta.content if chunk.choices else None
                if text:
                    self.wfile.write(encode_sse("delta", {"text": text}))
                    self.wfile.flush()
            self.wfile.write(encode_sse("done", {"request_id": request_id}))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            LOG.info("request_id=%s browser disconnected", request_id)

    def _send_json(self, status: HTTPStatus, payload: dict[str, str]) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, message: str, *args: object) -> None:
        LOG.info("client=%s %s", self.client_address[0], message % args)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    PortfolioHandler.stream_client = FintechStreamClient()
    server = ThreadingHTTPServer((HOST, PORT), PortfolioHandler)
    LOG.info("portfolio UI listening on http://%s:%s", HOST, PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()

