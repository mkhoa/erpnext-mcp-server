# src/prompts/prompts.py

# Import MCP types for defining prompts
from typing import List
from mcp.server import FastMCP
import mcp.types as types


# This is a general system prompt that sets the context for the AI assistant.
# It is used to initialize the MCP server's instructions for tool use.
SYSTEM_PROMPT = """
You are an expert AI assistant for ERPNext, powered by the Frappe Framework.
Your primary function is to help users interact with their ERPNext instance by understanding their natural language requests and translating them into actions using the provided tools.
If you need more information to use a tool (e.g., the schema of a DocType), use the `get_doctype_schema` tool first.
After executing the necessary tools, use their output to formulate a clear, natural language response to the user.
If you cannot fulfill the request or if it's ambiguous, ask for clarification. Do not make up information.
"""

# These are the raw f-string templates that correspond to the prompts defined above.
# The server logic uses these to construct the final message.
PAYLOAD_GENERATOR_TEMPLATE = """
Based on the user's request and the provided DocType schema, generate a valid JSON payload to create a new document.

**User Request:**
"{user_request}"

**DocType Schema for '{doctype_name}':**
```json
{doctype_schema}
```

**Instructions:**
1.  The payload MUST be a single JSON object.
2.  The `doctype` field in the payload must be set to '{doctype_name}'.
3.  Only include fields that are present in the schema.
4.  Pay close attention to the `reqd: true` fields in the schema; they are mandatory. If the user has not provided a value for a mandatory field, you MUST ask for it. Do not invent values.
5.  For fields of type 'Link', the value should be the 'name' (primary key) of the linked document.
6.  For fields of type 'Table', the value should be a list of JSON objects, where each object conforms to the schema of the child DocType.
7.  Do not include read-only (`read_only: true`) or hidden (`hidden: true`) fields in the payload.

Generate ONLY the JSON payload for the new document.
"""

QUERY_GENERATOR_TEMPLATE = """
Based on the user's request, generate a JSON object representing the 'filters' to be used with the `get_list` tool for the DocType '{doctype_name}'.

**User Request:**
"{user_request}"

**Relevant Fields from Schema for '{doctype_name}':**
```json
{relevant_fields}
```

**Instructions for generating filters:**
1.  The output must be a single JSON object.
2.  Each key in the object should be a valid `fieldname` from the schema.
3.  The value can be a simple value (e.g., {{"customer": "Acme Inc."}}) or a list for complex queries.
4.  For complex queries, use a list with the format `["operator", "value"]`. Common operators include `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `in`, `not in`.
    - Example: To find records with an amount greater than 1000, use `{{"amount": [">", 1000]}}`.
    - Example: To find records where the status is one of "Open" or "Pending", use `{{"status": ["in", ["Open", "Pending"]]}}`.

Generate ONLY the JSON filter object. If no specific filters are mentioned in the request, return an empty JSON object `{{}}`.
"""


def _register_prompts(mcp: FastMCP):
    """Registers all MCP prompts with the server."""

    @mcp.prompt(
        name="generate_payload",
        description="Generate a valid JSON payload to create a new ERPNext document.",
    )
    async def generate_payload(
        user_request: str, doctype_name: str, doctype_schema: str
    ) -> List[types.PromptMessage]:
        """
        Generates a prompt to an LLM to create a JSON payload for a new document.

        Args:
            user_request: The user's original natural language request for creating the document.
            doctype_name: The name of the DocType to create (e.g., 'Sales Order').
            doctype_schema: The full JSON schema of the DocType.
        """
        formatted_prompt = PAYLOAD_GENERATOR_TEMPLATE.format(
            user_request=user_request,
            doctype_name=doctype_name,
            doctype_schema=doctype_schema,
        )
        return [{"role": "user", "content": {"type": "text", "text": formatted_prompt}}]

    @mcp.prompt(
        name="generate_query_filters",
        description="Generate a JSON filter object for listing ERPNext documents based on a user request.",
    )
    async def generate_query_filters(
        user_request: str, doctype_name: str, relevant_fields: str
    ) -> List[types.PromptMessage]:
        """
        Generates a prompt to an LLM to create a JSON filter object for listing documents.

        Args:
            user_request: The user's original natural language request for listing documents.
            doctype_name: The name of the DocType to list (e.g., 'ToDo').
            relevant_fields: A JSON string of relevant fields from the DocType schema to help in filtering.
        """
        formatted_prompt = QUERY_GENERATOR_TEMPLATE.format(
            user_request=user_request,
            doctype_name=doctype_name,
            relevant_fields=relevant_fields,
        )
        return [{"role": "user", "content": {"type": "text", "text": formatted_prompt}}]