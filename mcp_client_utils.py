import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = "https://ertugrulerata-mcp-media-server.hf.space/sse"

async def _call_process_youtube_workflow_async(url: str):
    """
    Connects to the remote MCP server via SSE and calls the process_youtube_workflow tool.
    """
    print(f"Connecting to MCP Server: {MCP_SERVER_URL}")
    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Call the tool
            print(f"Calling tool 'process_youtube_workflow' with url: {url}")
            result = await session.call_tool("process_youtube_workflow", arguments={"url": url})

            # Extract text content from the result
            final_text = ""
            if result.content:
                for content in result.content:
                    if content.type == 'text':
                        final_text += content.text
            return final_text

def call_process_youtube_workflow(url: str):
    """
    Synchronous wrapper for the async MCP tool call.
    """
    try:
        # Create a new event loop for this thread if needed, or use asyncio.run
        return asyncio.run(_call_process_youtube_workflow_async(url))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"MCP Client Error: {str(e)}"
