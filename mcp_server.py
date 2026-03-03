from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from tools.tavily_tools import register_tavily_tools
from tools.db_tools import register_db_tools
from tools.telegram_tools import register_telegram_tools
from tools.scheduler_tools import register_scheduler_tools

load_dotenv()

# Initialize the main FastMCP server
mcp = FastMCP("MultiAgentToolsServer")

# Register all namespaces containing our sub-tools
register_tavily_tools(mcp)
register_db_tools(mcp)
register_telegram_tools(mcp)
register_scheduler_tools(mcp)

if __name__ == "__main__":
    # Start the FastMCP server via stdio
    mcp.run()
