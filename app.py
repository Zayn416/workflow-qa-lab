import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from db import NotFoundError, TaskStore, ValidationError


ROOT = Path(__file__).parent
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
TASK_PATH = re.compile(r"^/api/tasks/([1-9][0-9]*)(?:/(events))?$")


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValidationError("Invalid Content-Length.") from error
            if not 0 < length <= 8192:
                raise ValidationError("JSON body must be 1-8192 bytes.")
            try:
                payload = json.loads(self.rfile.read(length))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValidationError("Invalid JSON body.") from error
            if not isinstance(payload, dict):
                raise ValidationError("JSON body must be an object.")
            return payload

        def _handle_error(self, error):
            if isinstance(error, NotFoundError):
                self._send(404, {"error": str(error)})
            elif isinstance(error, ValidationError):
                self._send(400, {"error": str(error)})
            else:
                raise error

        def do_GET(self):
            if self.path in STATIC:
                filename, content_type = STATIC[self.path]
                body = (ROOT / filename).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/api/tasks":
                self._send(200, {"tasks": store.list_tasks()})
                return
            match = TASK_PATH.fullmatch(self.path)
            if match and match.group(2) == "events":
                try:
                    self._send(200, {"events": store.events(int(match.group(1)))})
                except (ValidationError, NotFoundError) as error:
                    self._handle_error(error)
                return
            self._send(404, {"error": "Not found."})

        def do_POST(self):
            if self.path != "/api/tasks":
                self._send(404, {"error": "Not found."})
                return
            try:
                payload = self._read_json()
                self._send(201, {"task": store.create_task(payload.get("title"), payload.get("priority"))})
            except (ValidationError, NotFoundError) as error:
                self._handle_error(error)

        def do_PATCH(self):
            match = TASK_PATH.fullmatch(self.path)
            if not match or match.group(2):
                self._send(404, {"error": "Not found."})
                return
            try:
                payload = self._read_json()
                self._send(200, {"task": store.transition(int(match.group(1)), payload.get("status"))})
            except (ValidationError, NotFoundError) as error:
                self._handle_error(error)

        def log_message(self, format, *args):
            pass

    return Handler


def make_server(host="127.0.0.1", port=8000, db_path="tasks.db"):
    return ThreadingHTTPServer((host, port), make_handler(TaskStore(db_path)))


if __name__ == "__main__":
    server = make_server(port=int(os.environ.get("PORT", "8000")), db_path=os.environ.get("DB_PATH", "tasks.db"))
    print(f"Workflow QA Lab: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
