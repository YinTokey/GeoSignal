import os
import asyncio
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

from agents.graph import build_agent_graph

load_dotenv()

# Store the global session to reuse it across telegram messages
_mcp_session: Optional[ClientSession] = None
_mcp_client_ctx = None
_reusable_agent = None

async def init_agent():
    """Initializes the MCP server connection and the Langchain Agent."""
    global _mcp_session, _mcp_client_ctx, _reusable_agent
    
    if _reusable_agent is not None:
        return _reusable_agent

    print("Initializing Agent and connecting to local MCP Server...")
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "mcp_server.py"],
        env=os.environ.copy()
    )

    _mcp_client_ctx = stdio_client(server_params)
    read, write = await _mcp_client_ctx.__aenter__()
    
    _mcp_session = ClientSession(read, write)
    await _mcp_session.__aenter__()
    
    # Initialize connection
    await _mcp_session.initialize()

    # Load tools from MCP Server
    tools = await load_mcp_tools(_mcp_session)
    print(f"Loaded {len(tools)} tools from MCP Server.")
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    
    # Create the Multi-Agent graph
    _reusable_agent = build_agent_graph(llm, tools)
    return _reusable_agent

async def close_agent():
    """Closes down the MCP connection."""
    global _mcp_session, _mcp_client_ctx
    if _mcp_session:
        await _mcp_session.__aexit__(None, None, None)
    if _mcp_client_ctx:
        await _mcp_client_ctx.__aexit__(None, None, None)
    print("Agent connection closed.")

async def run_agent(chat_id: int, message: str) -> None:
    """Passes a string message and chat ID to the multi-agent graph."""
    agent = await init_agent()
    
    print(f"Agent processing message: '{message}' for chat {chat_id}")
    
    initial_state = {
        "chat_id": chat_id,
        "user_message": message
    }
    
    # Async invoke
    try:
        final_state = await agent.ainvoke(initial_state)
        print("Final Agent State completed.")
    except Exception as e:
        print(f"Agent invocation failed: {e}")
