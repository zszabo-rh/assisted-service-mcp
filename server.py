# server.py
from mcp.server.fastmcp import FastMCP
import logging

# Create an MCP server
mcp = FastMCP("AssistedService")
logging.basicConfig(filename='/tmp/assisted-service-mcp-server.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    mcp.run()


@mcp.tool()
def cluster_info(cluster_id: str) -> str:
    """Print the information about the cluster with the given id"""

    logging.info(f"responding to a request for cluster info with id {cluster_id}")
    return "{\"name\": \"nicks-cluster\", \"id\": \"123\", \"type\": \"best\"}"
