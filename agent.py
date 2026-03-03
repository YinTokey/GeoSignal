import os
import asyncio
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

# The system prompt to instruct the agent to decompose, search, and synthesize
SYSTEM_PROMPT = """You are a helpful and intelligent AI agent. 
When asked a question, you should:
1. Understand and decompose the user's request into actionable search tasks.
2. Use the provided tools (e.g., Tavily Search via MCP) to find accurate, up-to-date information.
3. Synthesize the findings into a clear, cohesive, and concise response.
Always be helpful and polite."""

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
    
    # Create the ReAct agent
    _reusable_agent = create_react_agent(llm, tools, state_modifier=SYSTEM_PROMPT)
    return _reusable_agent

async def close_agent():
    """Closes down the MCP connection."""
    global _mcp_session, _mcp_client_ctx
    if _mcp_session:
        await _mcp_session.__aexit__(None, None, None)
    if _mcp_client_ctx:
        await _mcp_client_ctx.__aexit__(None, None, None)
    print("Agent connection closed.")

async def run_agent(message: str) -> str:
    """Passes a string message to the agent and gets the response."""
    agent = await init_agent()
    
    print(f"Agent processing message: {message}")
    inputs = {"messages": [HumanMessage(content=message)]}
    
    # Stream or invoke
    final_response = ""
    async for chunk in agent.astream(inputs, stream_mode="values"):
        message_obj = chunk["messages"][-1]
        final_response = message_obj.content
        # You can see the tool calls and intermediate steps here if needed
        # print("Step:", message_obj)
        
    return final_response
