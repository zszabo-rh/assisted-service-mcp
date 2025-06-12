from mcp.server.fastmcp import FastMCP
import json

from service_client import InventoryClient

mcp = FastMCP("AssistedService")

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)

@mcp.tool()
def cluster_info(cluster_id: str) -> str:
    """Get detailed information about the assisted installer cluster with the given id"""
    return InventoryClient().get_cluster(cluster_id=cluster_id).to_str()

@mcp.tool()
def list_clusters() -> str:
    """
    Lists all of the current user's assisted installer clusters.
    Returns only minimal cluster information, use cluster_info to get more detailed information
    """
    clusters = InventoryClient().list_clusters()
    resp = [{"name": cluster["name"], "id": cluster["id"], "openshift_version": cluster["openshift_version"], "status": cluster["status"]} for cluster in clusters]
    return json.dumps(resp)

@mcp.tool()
def cluster_events(cluster_id: str) -> str:
    """Get the events related to a cluster with the given id"""
    return InventoryClient().get_events(cluster_id=cluster_id)

@mcp.tool()
def host_events(cluster_id: str, host_id: str) -> str:
    """Get the events related to a host within a cluster"""
    return InventoryClient().get_events(cluster_id=cluster_id, host_id=host_id)

@mcp.tool()
def infraenv_info(infraenv_id: str) -> str:
    """
    Get detailed information about the assisted installer infra env with the given id
    This will contain data like the ISO download URL as well as infra env metadata
    """
    return InventoryClient().get_infra_env(infraenv_id).to_str()

@mcp.tool()
def create_cluster(name: str, version: str, base_domain: str, single_node: bool) -> str:
    """
    Create a new assisted installer cluster and infraenv with the given name, openshift version, and base domain.
    The single_node arg should be set to True only when the user specifically requests a single node cluster or no high availability
    Returns the created cluster id and infraenv id formatted as json.
    """
    client = InventoryClient()
    cluster = client.create_cluster(name, version, single_node, base_dns_domain=base_domain)
    infraenv = client.create_infra_env(name, cluster_id=cluster.id, openshift_version=cluster.openshift_version)
    return json.dumps({'cluster_id': cluster.id, 'infraenv_id': infraenv.id})

@mcp.tool()
def set_cluster_vips(cluster_id: str, api_vip: str, ingress_vip: str) -> str:
    """
    Set the API and ingress virtual IP addresses (VIPS) for the assisted installer cluster with the given ID
    """
    return InventoryClient().update_cluster(cluster_id, api_vip=api_vip, ingress_vip=ingress_vip).to_str()

@mcp.tool()
def install_cluster(cluster_id: str) -> str:
    """
    Trigger installation for the assisted installer cluster with the given id
    """
    return InventoryClient().install_cluster(cluster_id).to_str()

@mcp.tool()
def list_versions() -> str:
    """
    Lists the available OpenShift versions for installation with the assisted installer
    """
    return json.dumps(InventoryClient().get_openshift_versions(True))

@mcp.tool()
def list_operator_bundles() -> str:
    """
    Lists the operator bundles that can be optionally added to a cluster during installation
    """
    return json.dumps(InventoryClient().get_operator_bundles())

@mcp.tool()
def add_operator_bundle_to_cluster(cluster_id: str, bundle_name: str) -> str:
    """
    Request an operator bundle to be installed with the given cluster
    """
    return InventoryClient().add_operator_bundle_to_cluster(cluster_id, bundle_name).to_str()

@mcp.tool()
def set_host_role(host_id: str, infraenv_id: str, role: str) -> str:
    """
    Update a host to a specific role. The role options are 'auto-assign', 'master', 'arbiter', 'worker'
    """
    return InventoryClient().update_host(host_id, infraenv_id, host_role=role).to_str()
