from mcp.server.fastmcp import FastMCP
from tavily import AsyncTavilyClient
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("TavilySearchServer")

tavily_api_key = os.getenv("TAVILY_API_KEY")

@mcp.tool()
async def tavily_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for real-time information.
    
    Args:
        query: The search query.
        max_results: The maximum number of results to return.
    """
    if not tavily_api_key:
        return "Error: TAVILY_API_KEY is not set."
        
    client = AsyncTavilyClient(api_key=tavily_api_key)
    try:
        response = await client.search(query=query, max_results=max_results)
        
        # Format the results into a string
        results_str = f"Found {len(response.get('results', []))} results for '{query}':\n\n"
        for i, result in enumerate(response.get('results', []), 1):
            results_str += f"{i}. {result.get('title')}\n"
            results_str += f"URL: {result.get('url')}\n"
            results_str += f"Content: {result.get('content')}\n\n"
            
        return results_str
    except Exception as e:
        return f"Error executing search: {str(e)}"

if __name__ == "__main__":
    # Start the FastMCP server via stdio
    # This will be called by the agent client
    mcp.run()
