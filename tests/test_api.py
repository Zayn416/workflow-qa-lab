import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import make_server


class WorkflowApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "tasks.db"
        self.server = make_server(port=0, db_path=self.database)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.directory.cleanup()

    def call(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base_url + path, data=body, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_create_transition_and_audit(self):
        status, created = self.call("POST", "/api/tasks", {"title": "Check nightly build", "priority": "high"})
        self.assertEqual(status, 201)
        task_id = created["task"]["id"]
        self.assertEqual(created["task"]["status"], "open")
        self.assertEqual(self.call("PATCH", f"/api/tasks/{task_id}", {"status": "done"})[0], 400)
        self.assertEqual(self.call("PATCH", f"/api/tasks/{task_id}", {"status": "in_progress"})[0], 200)
        self.assertEqual(self.call("PATCH", f"/api/tasks/{task_id}", {"status": "done"})[0], 200)
        self.assertEqual(self.call("PATCH", f"/api/tasks/{task_id}", {"status": "in_progress"})[0], 200)
        events = self.call("GET", f"/api/tasks/{task_id}/events")[1]["events"]
        self.assertEqual([event["to_status"] for event in events], ["open", "in_progress", "done", "in_progress"])
        self.assertEqual(self.call("GET", "/api/tasks")[1]["tasks"][0]["status"], "in_progress")

    def test_validation_and_missing_task(self):
        self.assertEqual(self.call("POST", "/api/tasks", {"title": "x", "priority": "high"})[0], 400)
        self.assertEqual(self.call("POST", "/api/tasks", {"title": "Valid task", "priority": "urgent"})[0], 400)
        self.assertEqual(self.call("PATCH", "/api/tasks/999", {"status": "done"})[0], 404)
        self.assertEqual(self.call("GET", "/api/tasks/999/events")[0], 404)
        self.assertEqual(self.call("GET", "/missing")[0], 404)

    def test_static_frontend_and_database_persistence(self):
        with urlopen(self.base_url, timeout=3) as response:
            self.assertIn(b"Workflow QA Lab", response.read())
        created = self.call("POST", "/api/tasks", {"title": "Verify import", "priority": "normal"})[1]
        self.assertEqual(created["task"]["id"], 1)
        from db import TaskStore
        self.assertEqual(TaskStore(self.database).list_tasks()[0]["title"], "Verify import")


if __name__ == "__main__":
    unittest.main()
