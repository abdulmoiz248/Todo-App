import asyncio
import re
import json
from typing import Optional, List, Dict
from contextlib import AsyncExitStack
from groq import Groq
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.tools: List[Dict] = []
        self.exit_stack = AsyncExitStack()
        self.groq = Groq()
        self.conversation: List[Dict] = [
            {
                "role": "system",
                "content": (
                    "You are a ToDo assistant. You can use MCP tools: add_todo, delete_todo, "
                    "update_todo, update_status, get_todo, get_todos. "
                    "Keep track of all previous tasks. Ask only for missing info. "
                    "Always respond concisely."
                ),
            }
        ]

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("\n✅ Connected to MCP server with tools:", [tool.name for tool in tools])
        
        # Debug: print raw tool info (commented out for cleaner output)
        # for tool in tools:
        #     print(f"DEBUG: Raw tool {tool.name}:")
        #     print(f"  - inputSchema: {tool.inputSchema}")
        #     print(f"  - description: {tool.description}")
        
        self.tools = tools

        # convert to Groq function-calling schema immediately
        self.convert_to_groq_tools()

    async def cleanup(self):
        await self.exit_stack.aclose()

    def convert_to_groq_tools(self):
        groq_tools = []
        for tool in self.tools:
            # Handle tools with no parameters properly
            if tool.inputSchema:
                parameters = tool.inputSchema.copy()
                # Ensure required array exists
                if 'required' not in parameters:
                    parameters['required'] = []
            else:
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            
            groq_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters
                }
            }
            groq_tools.append(groq_tool)
            
            # Debug: print tool schema
            if tool.name == "get_todos":
                print(f"DEBUG: get_todos parameters: {json.dumps(parameters, indent=2)}")
                print(f"DEBUG: get_todos full tool: {json.dumps(groq_tool, indent=2)}")
            else:
                print(f"DEBUG: Converted tool {tool.name}: {json.dumps(groq_tool, indent=2)}")
            
        self.tools = groq_tools

    def extract_task_info(self, text: str):
        task_id_match = re.search(r"(?:task ?id[:\s]*)(\d+)", text, re.IGNORECASE)
        task_name_match = re.search(r"(?:task ?name[:\s]*)([^\n,]+)", text, re.IGNORECASE)
        desc_match = re.search(r"(?:description[:\s]*)(.+)", text, re.IGNORECASE)

        return {
            "task_id": int(task_id_match.group(1)) if task_id_match else None,
            "task_name": task_name_match.group(1).strip() if task_name_match else None,
            "description": desc_match.group(1).strip() if desc_match else None,
        }

    async def process_query(self, query: str):
        if not self.tools:
            raise RuntimeError("No tools loaded from MCP server.")

        extracted = self.extract_task_info(query)
        auto_call = None
        if extracted["task_id"] is not None and extracted["task_name"] is not None and extracted["description"] is not None:
            auto_call = {"name": "add_todo", "args": extracted}

        self.conversation.append({"role": "user", "content": query})

        # Debug: print tools being sent to Groq
        print(f"DEBUG: Sending {len(self.tools)} tools to Groq")
        for tool in self.tools:
            print(f"  - {tool['function']['name']}")

        response = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=self.conversation,
            tools=self.tools
        )

        full_text = ""
        if response.choices:
            msg = response.choices[0].message
            
            # Debug: print what Groq returned
            print(f"DEBUG: Groq response message: {msg}")
            print(f"DEBUG: Has tool_calls: {hasattr(msg, 'tool_calls')}")
            if hasattr(msg, "tool_calls"):
                print(f"DEBUG: Tool calls: {msg.tool_calls}")

            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"DEBUG: Processing {len(msg.tool_calls)} tool calls")
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    print(f"DEBUG: Calling tool {tool_name} with arguments: {tc.function.arguments}")
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except Exception as e:
                        print(f"DEBUG: Error parsing tool arguments: {e}")
                        tool_args = {}
                    try:
                        print(f"DEBUG: Calling MCP tool {tool_name} with args {tool_args}")
                        result = await self.session.call_tool(tool_name, tool_args)
                        print(f"DEBUG: MCP tool result: {result}")
                        tool_output = "".join(
                            [part.text for part in getattr(result, "content", []) if hasattr(part, "text")]
                        )
                        print(f"DEBUG: Tool output: {tool_output}")
                    except Exception as e:
                        print(f"DEBUG: Error calling tool {tool_name}: {e}")
                        tool_output = f"Error calling tool {tool_name}: {e}"

                    self.conversation.append({
                        "role": "function",
                        "name": tool_name,
                        "content": tool_output
                    })

                print(f"DEBUG: Making follow-up request to Groq...")
                followup = self.groq.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=self.conversation
                    # Don't include tools in follow-up to avoid infinite tool calls
                )
                print(f"DEBUG: Follow-up response: {followup.choices[0].message if followup.choices else 'No choices'}")
                if followup.choices and followup.choices[0].message.content:
                    full_text = followup.choices[0].message.content.strip()
                    print(f"DEBUG: Follow-up text: {full_text}")
                else:
                    print("DEBUG: No follow-up content generated")
            else:
                if msg.content:
                    full_text = msg.content.strip()

        if full_text:
            print(f"Groq: {full_text}")
            self.conversation.append({"role": "assistant", "content": full_text})

        if auto_call:
            result = await self.session.call_tool(auto_call["name"], auto_call["args"])
            tool_output = "".join(
                [part.get("text", "") for part in getattr(result, "content", []) if isinstance(part, dict)]
            )
            self.conversation.append({"role": "function", "name": auto_call["name"], "content": tool_output})


async def chat_loop(client: MCPClient):
    print("\n💬 Start chatting with Groq+MCP (type 'exit' to quit)\n")
    while True:
        query = input("You: ").strip()
        if query.lower() in ["exit", "quit"]:
            print("👋 Ending chat.")
            break

        try:
            await client.process_query(query)
        except Exception as e:
            print("⚠️ Error:", e)


async def main():
    client = MCPClient()
    try:
        await client.connect_to_server("C:/Users/Admin/Desktop/Todo mcp/mcp-server/server.py")
        await chat_loop(client)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
