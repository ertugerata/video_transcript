import asyncio
import base64
import os
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = "https://ertugrulerata-mcp-media-server.hf.space/sse"

async def _call_transcribe_audio_async(file_path: str, model_size: str = "base"):
    """
    Connects to the remote MCP server via SSE and calls the transcribe_audio_base64 tool.
    """
    print(f"Connecting to MCP Server: {MCP_SERVER_URL}")

    filename = os.path.basename(file_path)
    print(f"Preparing file {filename} for transfer...")

    # Read and encode file
    with open(file_path, "rb") as f:
        file_content = f.read()
        audio_data = base64.b64encode(file_content).decode("utf-8")

    print(f"Sending file '{filename}' ({len(file_content)} bytes) to MCP server for transcription...")

    async with sse_client(MCP_SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("transcribe_audio_base64", arguments={
                "audio_data": audio_data,
                "filename": filename,
                "model_size": model_size
            })

            final_text = ""
            if result.content:
                for content in result.content:
                    if content.type == 'text':
                        final_text += content.text
            return final_text

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

def call_transcribe_audio(file_path: str, model_size: str = "base"):
    """
    Synchronous wrapper for the async MCP tool call.
    """
    try:
        return asyncio.run(_call_transcribe_audio_async(file_path, model_size))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"MCP Client Error: {str(e)}"
