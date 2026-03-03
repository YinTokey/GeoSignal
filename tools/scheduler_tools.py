from mcp.server.fastmcp import FastMCP

def register_scheduler_tools(mcp: FastMCP):

    @mcp.tool()
    def set_schedule(job_name: str, cron_expr: str) -> str:
        """
        Placeholder tool for setting a scheduled cron job.
        For now, just acknowledges the request.
        """
        return f"Acknowledged request to schedule '{job_name}' at '{cron_expr}'. (Not implemented yet)"

    @mcp.tool()
    def pause_schedule(job_name: str) -> str:
        """
        Placeholder tool for pausing a scheduled cron job.
        """
        return f"Acknowledged request to pause '{job_name}'. (Not implemented yet)"
