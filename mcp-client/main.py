from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from client import MCPClient

client: MCPClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = MCPClient()
    await client.connect_to_server("C:/Users/Admin/Desktop/Todo mcp/mcp-server/server.py")
    yield
    if client:
        await client.cleanup()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to frontend domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat(query: str = Body(..., embed=True)):
    await client.process_query(query)
    last_msg = next((m for m in reversed(client.conversation) if m["role"] == "assistant"), None)
    return {"response": last_msg["content"] if last_msg else "No response"}
