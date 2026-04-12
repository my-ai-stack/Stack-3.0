# Model Context Protocol (MCP) Guide for Stack 3.0

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard that allows AI agents to seamlessly connect to external data sources and tools. Instead of writing custom integrations for every single service, MCP provides a unified way for agents to:

1. **Discover Tools**: Query a server for a list of available functions it can perform.
2. **Access Resources**: Read data from standardized URIs (e.g., `file:///logs/app.log` or `postgres://db/table`).
3. **Execute Actions**: Call tools on remote servers with a consistent JSON-RPC based interface.

In Stack 3.0, MCP is implemented as a bridge. The `MCPTool` allows the agent to route requests to configured MCP servers, making the agent's capabilities extensible without modifying the core codebase.

## Implementing a New MCP Server

To add new capabilities to the agent via MCP, you can create an MCP server using the official MCP SDK (available in TypeScript and Python).

### Basic Server Structure (Conceptual Python)

```python
from mcp.server import Server

# Create server instance
server = Server("my-custom-server")

# Register a tool
@server.tool()
def fetch_customer_data(customer_id: str) -> str:
    """Fetches customer data from the internal CRM."""
    # Implementation here
    return f"Data for customer {customer_id}: ..."

# Register a resource
@server.resource("customer://{id}/profile")
def get_profile(id: str) -> str:
    """Returns the profile of a customer."""
    return f"Profile for {id}..."

if __name__ == "__main__":
    server.run()
```

## Adding MCP Servers to Stack 3.0

MCP servers are managed via a configuration file located at `~/.stack-3.0/mcp_config.json`.

### Configuration Format

The configuration is a JSON object containing a `servers` map. Each entry defines how to start the server.

```json
{
  "servers": {
    "weather-service": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-weather"],
      "env": {
        "WEATHER_API_KEY": "your_key_here"
      },
      "enabled": true
    },
    "filesystem-server": {
      "command": "python3",
      "args": ["/path/to/mcp-fs-server.py", "/Users/walidsobhi/documents"],
      "enabled": true
    }
  }
}
```

### Managing Servers via Agent Tools

You can also manage these servers directly using the agent's built-in MCP tools:
- `mcp_add_server`: Add a new server configuration.
- `mcp_list_servers`: List all currently configured servers.
- `mcp_call`: Execute a tool on a specific server.
- `read_mcp_resource`: Retrieve content from a resource URI.
