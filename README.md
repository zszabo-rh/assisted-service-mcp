# Assisted Service MCP Server

MCP server for interracting with the OpenShift assisted installer API.

Diagnose cluster failures and find out how to fix them.

Try it out:

1. Clone the repo:
```
git clone git@github.com:carbonin/assisted-service-mcp.git
```

2. Get your OpenShift API token from https://cloud.redhat.com/openshift/token

3. The server is started and configured differently depending on what transport you want to use

For STDIO:

In VSCode for example:
```json
   "mcp": {
        "servers": {
            "AssistedService": {
                "command": "uv",
                "args": [
                    "--directory",
                    "/path/to/assisted-service-mcp",
                    "run",
                    "mcp",
                    "run",
                    "/path/to/assisted-service-mcp/server.py"
                ],
                "env": {
                    "OFFLINE_TOKEN": <your token>
                }
            }
        }
    }
```

For SSE (recommended):

Start the server in a terminal:

`OFFLINE_TOKEN=<your token> uv run --with mcp mcp run --transport=sse ./server.py`

Configure the server in the client:

```json
    "assisted-sse": {
      "transport": "sse",
      "url": "http://localhost:8000/sse"
    }
```

### Providing the Offline Token via Request Header

If you do not set the `OFFLINE_TOKEN` environment variable, you can provide the token as a request header.
When configuring your MCP client, add the `OCM-Offline-Token` header:

```json
    "assisted-sse": {
      "transport": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "OCM-Offline-Token": "<your token>"
      }
    }
```

4. Ask about your clusters:
![Example prompt asking about a cluster](images/cluster-prompt-example.png)
