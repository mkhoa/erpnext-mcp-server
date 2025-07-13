# ERPNext MCP Server

This project provides a server that acts as a middleware to expose ERPNext/Frappe API functionalities as tools for a Model-Context Protocol (MCP) client. It simplifies interactions with ERPNext by wrapping common API calls into easy-to-use Python functions.

## Overview

The core of this project is the `FrappeClient` class located in `src/utils/frappeclient.py`. This client handles authentication and communication with a Frappe/ERPNext instance. New functionalities can be easily added as methods to this class and then registered as tools in the MCP server.

## Features

The `FrappeClient` provides methods for various ERPNext operations, including:

*   **Document Management:**
    *   `get_list(doctype, ...)`: Fetch a list of documents.
    *   `get_doc(doctype, name, ...)`: Fetch a single document.
    *   `insert(doc)`: Create a new document.
    *   `update(doc)`: Update an existing document.
    *   `delete(doctype, name)`: Delete a document.
*   **Specific Business Lookups (MCP Tools):**
    *   `get_customer_code(customer_name)`: Look up a Customer Code by Customer Name.
    *   `get_item_code(item_query)`: Look up an Item Code by its name or description.
    *   `get_stock_balance(item_code)`: Query the stock balance for a specific item.
    *   `get_customer_outstanding_balance(customer_code)`: Query the outstanding Accounts Receivable (AR) balance for a customer.
*   **Other Utilities:**
    *   `get_pdf(doctype, name, ...)`: Download a document as a PDF.
    *   `rename_doc(doctype, old_name, new_name)`: Rename a document.

## Setup and Configuration

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd erpnext-mcp-server
    ```

2.  **Create a virtual environment:**
    It's recommended to use a virtual environment to manage project dependencies.
    ```bash
    # For Unix/macOS
    python3 -m venv .venv
    source .venv/bin/activate

    # For Windows
    python -m venv .venv
    .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    This project uses `uv` for dependency management, with dependencies defined in `pyproject.toml`.
    
    The `mcp dev` command in the next step will handle creating an environment and installing dependencies automatically from `pyproject.toml`.
4.  **Configure Environment Variables:**
    Create a `.env` file in the root of the project directory. This file will store the credentials for your ERPNext instance. Add the following variables to it:

    ```env
    FRAPPE_URL=https://your-erpnext-site.com
    FRAPPE_API_KEY=your_api_key
    FRAPPE_API_SECRET=your_api_secret
    ```

    You can generate API keys in your ERPNext instance by navigating to `User Menu > My Settings > API Access`.

## Usage

After configuring your `.env` file, you can run the MCP server in development mode. This will start the server and connect it to the MCP Inspector, which provides a UI for interacting with your server.

1.  **Run the server:**
    Make sure your virtual environment is activated. From your project's root directory, execute the following command:
    ```bash
    uv run mcp dev main.py
    ```

2.  **Interact with the MCP Inspector:**
    This command will launch the MCP Inspector in your web browser. You can use it to send requests to your server, view tool definitions, and debug your implementation. The server will automatically reload when you make changes to the source code.

    ![mcp_inspector](misc/mcp_inspector.png)