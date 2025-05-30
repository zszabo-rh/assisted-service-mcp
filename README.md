# Assisted Service MCP Server

MCP server for interracting with the OpenShift assisted installer API.

Diagnose cluster failures and find out how to fix them.

Try it out:

Clone the repo:
```
git clone git@github.com:carbonin/assisted-service-mcp.git
```

Get your OpenShift API token from https://cloud.redhat.com/openshift/token

Configure the MCP server in the client of your choice
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

Ask about your clusters:
![Example prompt asking about a cluster](images/cluster-prompt-example.png)
