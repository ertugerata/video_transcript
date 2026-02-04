import asyncio
import base64
import os
import math
import uuid
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://ertugrulerata-mcp-media-server.hf.space/sse")
CHUNK_SIZE = 1 * 1024 * 1024  # 1MB chunks

async def check_connection_async():
    """
    Checks if the MCP server is reachable.
    """
    try:
        async with sse_client(MCP_SERVER_URL, timeout=5, sse_read_timeout=5) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return True
    except Exception as e:
        print(f"MCP Connection Check Failed: {e}")
        return False

def check_connection():
    """
    Synchronous wrapper for connection check.
    """
    try:
        return asyncio.run(check_connection_async())
    except Exception as e:
        print(f"MCP Connection Check Error: {e}")
        return False

async def upload_file_chunked(file_path: str, session: ClientSession) -> str:
    """
    Uploads a file in chunks using the upload_chunk tool.
    Returns the upload_id.
    """
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    upload_id = str(uuid.uuid4())

    print(f"Uploading {filename} ({file_size} bytes) in {total_chunks} chunks. Upload ID: {upload_id}")

    with open(file_path, "rb") as f:
        for i in range(total_chunks):
            chunk = f.read(CHUNK_SIZE)
            chunk_data = base64.b64encode(chunk).decode("utf-8")

            print(f"Uploading chunk {i+1}/{total_chunks}...")

            result = await session.call_tool("upload_chunk", arguments={
                "upload_id": upload_id,
                "chunk_index": i,
                "chunk_data": chunk_data
            })

            # Check result for error
            result_text = ""
            if result.content:
                for content in result.content:
                    if content.type == 'text':
                        result_text += content.text

            if result_text.startswith("Error"):
                raise Exception(f"Failed to upload chunk {i}: {result_text}")

    print(f"Upload complete for {filename} (ID: {upload_id})")
    return upload_id

async def _call_transcribe_audio_async(file_path: str, model_size: str = "base"):
    """
    Connects to the remote MCP server via SSE and calls the transcribe_audio_base64 tool.
    If file is large (>5MB), uses chunked upload strategy.
    """
    print(f"Connecting to MCP Server: {MCP_SERVER_URL}")

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # Check if we should use chunked upload (e.g., > 5MB)
    use_chunked = file_size > 5 * 1024 * 1024

    # Set timeout to 1 hour (3600s) for large file uploads and long processing
    async with sse_client(MCP_SERVER_URL, timeout=3600, sse_read_timeout=3600) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if use_chunked:
                try:
                    # Check if upload_chunk exists
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]

                    if "upload_chunk" in tool_names:
                        print(f"File size {file_size} bytes > 5MB. Using chunked upload strategy.")
                        upload_id = await upload_file_chunked(file_path, session)

                        print(f"Requesting transcription for uploaded file: {filename} (ID: {upload_id})")
                        result = await session.call_tool("transcribe_uploaded_file", arguments={
                            "upload_id": upload_id,
                            "filename": filename,
                            "model_size": model_size
                        })
                    else:
                        print("Chunked upload tools not found on server. Falling back to base64.")
                        use_chunked = False
                except Exception as e:
                    print(f"Error checking/using chunked upload: {e}. Falling back to base64.")
                    use_chunked = False

            if not use_chunked:
                print(f"Preparing file {filename} for transfer (Legacy Base64)...")
                # Read and encode file
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    audio_data = base64.b64encode(file_content).decode("utf-8")

                print(f"Sending file '{filename}' ({len(file_content)} bytes) to MCP server for transcription...")

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
    # Set timeout to 1 hour (3600s) for long youtube video processing
    async with sse_client(MCP_SERVER_URL, timeout=3600, sse_read_timeout=3600) as (read, write):
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

async def _call_convert_media_async(file_path: str, target_format: str = "mp3"):
    """
    Connects to the remote MCP server via SSE and calls the convert_media_base64 tool.
    """
    print(f"Connecting to MCP Server: {MCP_SERVER_URL}")

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    use_chunked = file_size > 5 * 1024 * 1024

    async with sse_client(MCP_SERVER_URL, timeout=3600, sse_read_timeout=3600) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if use_chunked:
                try:
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools]

                    if "upload_chunk" in tool_names:
                        print(f"File size {file_size} bytes > 5MB. Using chunked upload strategy.")
                        upload_id = await upload_file_chunked(file_path, session)

                        print(f"Requesting conversion for uploaded file: {filename} (ID: {upload_id})")
                        result = await session.call_tool("convert_uploaded_file", arguments={
                            "upload_id": upload_id,
                            "filename": filename,
                            "output_format": target_format
                        })
                    else:
                        print("Chunked upload tools not found. Falling back.")
                        use_chunked = False
                except Exception as e:
                     print(f"Error checking/using chunked upload: {e}. Falling back.")
                     use_chunked = False

            if not use_chunked:
                print(f"Preparing file {filename} for conversion...")

                # Read and encode file
                with open(file_path, "rb") as f:
                    file_content = f.read()
                    audio_data = base64.b64encode(file_content).decode("utf-8")

                print(f"Sending file '{filename}' ({len(file_content)} bytes) to MCP server for conversion...")

                result = await session.call_tool("convert_media_base64", arguments={
                    "audio_data": audio_data,
                    "filename": filename,
                    "output_format": target_format
                })

            final_text = ""
            if result.content:
                for content in result.content:
                    if content.type == 'text':
                        final_text += content.text
            return final_text

def call_convert_media(file_path: str, target_format: str = "mp3"):
    """
    Synchronous wrapper for the async MCP tool call.
    """
    try:
        return asyncio.run(_call_convert_media_async(file_path, target_format))
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
