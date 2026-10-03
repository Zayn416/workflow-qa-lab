const form = document.querySelector("#task-form");
const tasksNode = document.querySelector("#tasks");
const messageNode = document.querySelector("#message");

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

function showMessage(error) {
  messageNode.textContent = error instanceof Error ? error.message : "";
}

function makeButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", async () => {
    button.disabled = true;
    try { await onClick(); showMessage(""); }
    catch (error) { showMessage(error); }
    finally { button.disabled = false; }
  });
  return button;
}

function renderTask(task) {
  const item = document.createElement("article");
  item.className = "task";
  const head = document.createElement("div");
  head.className = "task-head";
  const details = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = task.title;
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = `#${task.id} - ${task.priority} priority - created ${new Date(task.created_at).toLocaleString()}`;
  details.append(title, meta);
  const status = document.createElement("span");
  status.className = "status";
  status.textContent = task.status.replace("_", " ");
  head.append(details, status);
  item.append(head);

  const actions = document.createElement("div");
  actions.className = "actions";
  const next = { open: ["Start", "in_progress"], in_progress: ["Complete", "done"], done: ["Reopen", "in_progress"] }[task.status];
  actions.append(makeButton(next[0], async () => {
    await request(`/api/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ status: next[1] }) });
    await loadTasks();
  }));
  actions.append(makeButton("History", async () => {
    const old = item.querySelector(".events");
    if (old) { old.remove(); return; }
    const { events } = await request(`/api/tasks/${task.id}/events`);
    const list = document.createElement("ol");
    list.className = "events";
    for (const event of events) {
      const row = document.createElement("li");
      row.textContent = `${event.from_status || "Created"} -> ${event.to_status} (${new Date(event.created_at).toLocaleString()})`;
      list.append(row);
    }
    item.append(list);
  }));
  item.append(actions);
  return item;
}

async function loadTasks() {
  const { tasks } = await request("/api/tasks");
  tasksNode.replaceChildren(...tasks.map(renderTask));
  if (!tasks.length) tasksNode.textContent = "No tasks yet.";
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const submit = form.querySelector("button[type=submit]");
  submit.disabled = true;
  try {
    await request("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title: form.elements.namedItem("title").value, priority: form.elements.namedItem("priority").value }),
    });
    form.reset();
    await loadTasks();
    showMessage("");
  } catch (error) { showMessage(error); }
  finally { submit.disabled = false; }
});

document.querySelector("#refresh").addEventListener("click", () => loadTasks().catch(showMessage));
loadTasks().catch(showMessage);
