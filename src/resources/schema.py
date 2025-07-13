import asyncio
import os
import logging
import json

from mcp.server.fastmcp.server import Context, FastMCP
from typing import Any, Dict, List
import mcp.types as types
from src.utils.frappeclient import FrappeClient, FrappeException

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    filename="frappe_mcp.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_doctype_schema(client: FrappeClient, doctype_name: str) -> Dict[str, Any]:
    """
    Fetches the raw schema for a given DocType from Frappe.

    Args:
        client: An authenticated FrappeClient instance.
        doctype_name: The name of the DocType to fetch (e.g., "Sales Order").

    Returns:
        A dictionary representing the DocType's raw schema.

    Raises:
        FrappeException: If the DocType is not found or another API error occurs.
    """
    try:
        # In Frappe, DocType metadata is stored in a document of type "DocType".
        doctype_meta = client.get_doc("DocType", doctype_name)
        if not doctype_meta:
            raise FrappeException(f"DocType '{doctype_name}' not found or no data returned.")
        
        # Return the raw dictionary without Pydantic validation.
        return doctype_meta
    except FrappeException:
        # Re-raise known exceptions from the client
        raise
    except Exception as e:
        raise FrappeException(f"An unexpected error occurred while fetching schema for '{doctype_name}': {e}")


def _register_resources(mcp: FastMCP):
    """Register all Frappe MCP resources."""

    @mcp.resource(uri="resource://schema/{doctype_name}",
                  name="GetDocTypeSchema",
                  description="An MCP resource that provides the JSON schema for a given Frappe DocType."
    )
    async def get_doctype_schema_resource(doctype_name: str) -> List[types.TextContent]:
        """
        An MCP resource that provides the JSON schema for a given Frappe DocType.
        """
        # The context is retrieved from the MCP instance, which is available
        # during a request. It is not passed as a direct argument to resource handlers.
        ctx = mcp.get_context()
        # Get the shared client instance from the application context
        client: FrappeClient = ctx.fastmcp.frappe_client

        logger.info(f"Getting schema for DocType: {doctype_name}")
        try:
            # Run the synchronous client call in a separate thread to avoid blocking
            schema_dict: Dict[str, Any] = await asyncio.to_thread(get_doctype_schema, client, doctype_name)
            # Return a JSON string for the LLM to easily understand and process.
            # The return value must be a list of ContentBlocks.
            # Use default=str to handle non-serializable types like datetime objects.
            return [{"type": "text", "text": json.dumps(schema_dict, indent=2, default=str)}]
        except FrappeException as e:
            logger.error(f"Error getting schema for {doctype_name}: {e}")
            return [{"type": "text", "text": json.dumps({"error": str(e)})}]
        except Exception as e:
            logger.error(f"Unexpected error getting schema for {doctype_name}: {e}", exc_info=True)
            return [{"type": "text", "text": json.dumps({"error": f"An unexpected error occurred: {str(e)}"})}]