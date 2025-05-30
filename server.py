# server.py
from mcp.server.fastmcp import FastMCP
import os

from service_client import InventoryClient

# Create an MCP server
mcp = FastMCP("AssistedService")

if __name__ == "__main__":
    mcp.run()

def get_client() -> InventoryClient:
    token = os.environ["OFFLINE_TOKEN"]
    return InventoryClient(token)


@mcp.tool()
def cluster_info(cluster_id: str) -> str:
    """Get detailed information about the assisted installer cluster with the given id"""
    return get_client().get_cluster(cluster_id=cluster_id).to_str()

@mcp.tool()
def cluster_events(cluster_id: str) -> str:
    """Get the events related to a cluster with the given id"""

    return get_client().get_events(cluster_id=cluster_id)

@mcp.tool()
def host_events(cluster_id: str, host_id: str) -> str:
    """Get the events related to a host with within a cluster"""

    return get_client().get_events(cluster_id=cluster_id, host_id=host_id)

@mcp.tool()
def infraenv_info(infraenv_id: str) -> str:
    """Get detailed information about the assisted installer infra env with the given id"""

    return get_client().get_infra_env(infraenv_id)
