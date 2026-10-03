# Workflow QA Lab

A new personal portfolio demo of a small task workflow, built with AI assistance in October 2026. It combines a browser interface, a Python HTTP API, SQLite persistence, and automated integration tests. It is not a company project or evidence of earlier employment or maintenance history.

## What it does

- Creates tasks with a title and priority.
- Moves tasks through `open -> in_progress -> done`; a completed task can be reopened.
- Records every status change in an audit log.
- Returns structured errors for invalid input and unsupported transitions.
- Serves a small browser interface from the same server as the API.

## Run

Requires Python 3.10 or newer. There are no third-party runtime dependencies.

```powershell
py -3 app.py
```

Open `http://127.0.0.1:8000`. Set `PORT` and `DB_PATH` to change the listening port or SQLite file.

## Test

```powershell
py -3 -m unittest discover -s tests -v
```

The integration suite starts a local server on an ephemeral port and checks validation, persistence, state transitions, and the audit trail through HTTP. Its temporary database is removed after each test. The sample task names used in tests are fictional.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/tasks` | List tasks, newest first |
| `POST` | `/api/tasks` | Create a task with `title` and `priority` |
| `PATCH` | `/api/tasks/{id}` | Set `status` to `in_progress`, `done`, or `open` |
| `GET` | `/api/tasks/{id}/events` | Read the status audit trail |

Example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/tasks -ContentType application/json -Body '{"title":"Check nightly build","priority":"high"}'
```

## Scope

This is a local demonstration, not a production service. It has no authentication, multi-user permissions, or deployment configuration. Do not put confidential or personal data into it.
