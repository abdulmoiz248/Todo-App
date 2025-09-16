import json
import logging
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TODO MCP SERVER")

DATA_FILE = "todos.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("todo.log"),
        logging.StreamHandler()
    ]
)

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@mcp.tool(description="Add a new todo with task_id, task_name, and description")
def add_todo(task_id, task_name, description):
    todos = load_data()
    new_todo = {"task_id": task_id, "task_name": task_name, "description": description, "status": "pending"}
    todos.append(new_todo)
    save_data(todos)
    logging.info(f"Added todo: {new_todo}")
    return new_todo

@mcp.tool(description="Delete a todo by its task_id")
def delete_todo(task_id):
    todos = load_data()
    todos = [t for t in todos if t["task_id"] != task_id]
    save_data(todos)
    logging.info(f"Deleted todo with id: {task_id}")
    return {"deleted_id": task_id}

@mcp.tool(description="Update the name and description of an existing todo")
def update_todo(task_id, task_name, description):
    todos = load_data()
    updated = None
    for t in todos:
        if t["task_id"] == task_id:
            t["task_name"] = task_name
            t["description"] = description
            updated = t
            break
    save_data(todos)
    logging.info(f"Updated todo: {updated}")
    return updated

@mcp.tool(description="Update the status of a todo (e.g., pending, done)")
def update_status(task_id, status):
    todos = load_data()
    updated = None
    for t in todos:
        if t["task_id"] == task_id:
            t["status"] = status
            updated = t
            break
    save_data(todos)
    logging.info(f"Updated status: {updated}")
    return updated

@mcp.tool(description="Fetch a todo by its task_id")
def get_todo(task_id):
    todos = load_data()
    todo = next((t for t in todos if t["task_id"] == task_id), None)
    logging.info(f"Fetched todo: {todo}")
    return todo

@mcp.tool(description="Fetch all todos")
def get_todos():
    todos = load_data()
    logging.info("Fetched all todos")
    return todos

if __name__ == "__main__":
    mcp.run()
