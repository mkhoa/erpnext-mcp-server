import os
import logging
from contextlib import asynccontextmanager

# Assuming the user is using the mcp-server library as hinted by the original file
from dotenv import load_dotenv
from mcp.server import FastMCP
from src.tools.tools import _register_tools
from src.resources.schema import _register_resources
from src.prompts.prompts import _register_prompts
from src.utils.frappeclient import FrappeClient
from src.prompts import prompts

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    filename="frappe_mcp.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Handles startup and shutdown events for the MCP server."""
    logger.info("Server starting up...")
    # Create a single, shared FrappeClient and attach it to the app instance
    # so it can be accessed from tools via the context.
    app.frappe_client = FrappeClient()
    logger.info("Frappe client created.")
    yield  # The server is now running
    logger.info("Server shutting down...")
    app.frappe_client.session.close()
    logger.info("Frappe client session closed. Shutdown complete.")

mcp = FastMCP(name="frappe-mcp", instructions=prompts.SYSTEM_PROMPT, lifespan=lifespan)

_register_tools(mcp)
_register_resources(mcp)
_register_prompts(mcp)

def main():
    """Script entry point to run the MCP server."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()