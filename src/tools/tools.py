import json
import logging
import os
import inspect
import asyncio
# Use python-dotenv to load environment variables from a .env file
from dotenv import load_dotenv
# Assuming the user is using the mcp-server library as hinted by the original file
from mcp.server.fastmcp.server import Context, FastMCP
from typing import Any, List, Callable
import mcp.types as types
from src.utils.frappeclient import FrappeClient, FrappeException

# Load environment variables from .env file in the project root
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    filename="frappe_mcp.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _create_tool_for_client_method(method_name: str, method: Callable[..., Any]) -> Callable[..., Any]:
    """
    Dynamically creates an async MCP tool function for a given FrappeClient method.

    This factory generates a wrapper function that:
    1. Has a precise signature matching the original method for MCP schema generation.
    2. Injects the MCP Context.
    3. Calls the synchronous FrappeClient method in a thread-safe way.
    4. Formats the output and handles errors.
    """
    original_sig = inspect.signature(method)

    # The actual implementation of the tool
    async def tool_wrapper(ctx: Context, **kwargs: Any) -> List[types.TextContent]:
        logger.info(f"Executing tool '{method_name}' with arguments: {kwargs}")
        try:
            # Get the shared client instance from the application context
            client: FrappeClient = ctx.fastmcp.frappe_client
            # Get the actual method from the client instance
            client_method = getattr(client, method_name)

            # Run the synchronous client call in a separate thread to avoid blocking the event loop
            result = await asyncio.to_thread(client_method, **kwargs)

            # The return value must be a list of ContentBlocks.
            # Use default=str to handle non-serializable types like datetime.
            return [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]
        except FrappeException as e:
            logger.error(f"FrappeException in tool '{method_name}': {e}")
            return [{"type": "text", "text": json.dumps({"error": str(e)})}]
        except Exception as e:
            logger.error(f"Unexpected error in tool '{method_name}': {e}", exc_info=True)
            return [{"type": "text", "text": json.dumps({"error": f"An unexpected error occurred: {str(e)}"})}]

    # Build the signature for the tool function that MCP will inspect.
    # This is crucial for MCP to understand the tool's arguments.
    tool_params = [
        inspect.Parameter('ctx', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context)
    ]
    for param in original_sig.parameters.values():
        if param.name != 'self':
            tool_params.append(param)

    tool_sig = inspect.Signature(parameters=tool_params, return_annotation=List[types.TextContent])

    # Attach the signature and other metadata to the wrapper
    tool_wrapper.__signature__ = tool_sig
    tool_wrapper.__name__ = method_name
    tool_wrapper.__doc__ = method.__doc__ or f"A tool to call FrappeClient's '{method_name}' method."

    return tool_wrapper


def _register_tools(mcp: FastMCP):
    """Inspects FrappeClient and dynamically registers its public methods as MCP tools."""
    # Methods to exclude from being registered as tools
    exclude_methods = {
        '__init__', '__enter__', '__exit__', 'login', 'logout', 'authenticate',
        'post_process', 'post_process_file_stream', 'preprocess',
        'get_request', 'post_request'
    }

    for name, method in inspect.getmembers(FrappeClient, predicate=inspect.isfunction):
        # Register public methods that are not in the exclusion list
        if not name.startswith('_') and name not in exclude_methods:
            tool_func = _create_tool_for_client_method(name, method)
            mcp.add_tool(tool_func)
            logger.info(f"Registered FrappeClient method as tool: '{name}'")