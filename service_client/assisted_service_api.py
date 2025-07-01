"""
Client for Red Hat Assisted Service API.

This module provides the InventoryClient class for interacting with Red Hat's
Assisted Service API to manage OpenShift cluster installations, infrastructure
environments, and host management.
"""

import os
import asyncio
from typing import Any, Optional, cast
from urllib.parse import urlparse

import requests
from assisted_service_client import ApiClient, Configuration, api, models

from service_client.logger import log


class InventoryClient:
    """
    Client for interacting with Red Hat Assisted Service API.

    This class provides methods to manage OpenShift clusters, infrastructure
    environments, hosts, and installation workflows through the Red Hat
    Assisted Service API.

    Args:
        access_token (str): The access token for authenticating with the API.
    """

    def __init__(self, access_token: str):
        """Initialize the InventoryClient with an access token."""
        self.access_token = access_token
        self.pull_secret = self._get_pull_secret()
        self.inventory_url = os.environ.get(
            "INVENTORY_URL", "https://api.openshift.com/api/assisted-install/v2"
        )
        self.client_debug = os.environ.get("CLIENT_DEBUG", "False").lower() == "true"

    def _get_pull_secret(self) -> str:
        url = os.environ.get(
            "PULL_SECRET_URL",
            "https://api.openshift.com/api/accounts_mgmt/v1/access_token",
        )
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text

    def _get_client(self) -> ApiClient:
        configs = Configuration()
        configs.host = self._get_host(configs)
        configs.debug = self.client_debug
        configs.api_key_prefix["Authorization"] = "Bearer"
        configs.api_key["Authorization"] = self.access_token
        return ApiClient(configuration=configs)

    def _installer_api(self) -> api.InstallerApi:
        api_client = self._get_client()
        return api.InstallerApi(api_client=api_client)

    def _events_api(self) -> api.EventsApi:
        api_client = self._get_client()
        return api.EventsApi(api_client=api_client)

    def _operators_api(self) -> api.OperatorsApi:
        api_client = self._get_client()
        return api.OperatorsApi(api_client=api_client)

    def _versions_api(self) -> api.VersionsApi:
        api_client = self._get_client()
        return api.VersionsApi(api_client=api_client)

    def _get_host(self, configs: Configuration) -> str:
        parsed_host = urlparse(configs.host)
        parsed_inventory_url = urlparse(self.inventory_url)
        return parsed_host._replace(
            netloc=parsed_inventory_url.netloc, scheme=parsed_inventory_url.scheme
        ).geturl()

    async def get_cluster(
        self, cluster_id: str, get_unregistered_clusters: bool = False
    ) -> models.Cluster:
        """
        Get cluster information by ID.

        Args:
            cluster_id: The unique identifier of the cluster.
            get_unregistered_clusters: Whether to include unregistered clusters.

        Returns:
            models.Cluster: The cluster object containing cluster information.
        """
        return cast(
            models.Cluster,
            await asyncio.to_thread(
                self._installer_api().v2_get_cluster,
                cluster_id=cluster_id,
                get_unregistered_clusters=get_unregistered_clusters,
            ),
        )

    async def list_clusters(self) -> list:
        """
        List all clusters accessible to the authenticated user.

        Returns:
            list: A list of cluster objects.
        """
        return cast(
            list, await asyncio.to_thread(self._installer_api().v2_list_clusters)
        )

    async def get_events(
        self,
        cluster_id: Optional[str] = "",
        host_id: Optional[str] = "",
        infra_env_id: Optional[str] = "",
        categories: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Get events for clusters, hosts, or infrastructure environments.

        Args:
            cluster_id: Optional cluster ID to filter events.
            host_id: Optional host ID to filter events.
            infra_env_id: Optional infrastructure environment ID to filter events.
            categories: List of event categories to filter. Defaults to ["user"].
            **kwargs: Additional parameters for the API call.

        Returns:
            str: Raw event data as a json string.
        """
        if categories is None:
            categories = ["user"]
        log.info(
            "Downloading events for cluster %s, host %s, infraenv %s, categories %s",
            cluster_id,
            host_id,
            infra_env_id,
            categories,
        )
        response = await asyncio.to_thread(
            self._events_api().v2_list_events,
            cluster_id=cluster_id,
            host_id=host_id,
            infra_env_id=infra_env_id,
            categories=categories,
            _preload_content=False,
            **kwargs,
        )
        return cast(Any, response).data

    async def get_infra_env(self, infra_env_id: str) -> models.InfraEnv:
        """
        Get infrastructure environment information by ID.

        Args:
            infra_env_id: The unique identifier of the infrastructure environment.

        Returns:
            models.InfraEnv: The infrastructure environment object.
        """
        return cast(
            models.InfraEnv,
            await asyncio.to_thread(
                self._installer_api().get_infra_env, infra_env_id=infra_env_id
            ),
        )

    async def create_cluster(
        self, name: str, version: str, single_node: bool, **cluster_params: Any
    ) -> models.Cluster:
        """
        Create a new OpenShift cluster.

        Args:
            name: The name of the cluster.
            version: The OpenShift version to install.
            single_node: Whether to create a single-node cluster.
            **cluster_params: Additional cluster configuration parameters.

        Returns:
            models.Cluster: The created cluster object.
        """
        if single_node:
            cluster_params["control_plane_count"] = 1
            cluster_params["high_availability_mode"] = "None"
            cluster_params["user_managed_networking"] = True

        params = models.ClusterCreateParams(
            name=name,
            openshift_version=version,
            pull_secret=self.pull_secret,
            **cluster_params,
        )
        log.info("Creating cluster with params %s", params.__dict__)
        result = await asyncio.to_thread(
            self._installer_api().v2_register_cluster, new_cluster_params=params
        )
        return cast(models.Cluster, result)

    async def create_infra_env(
        self, name: str, **infra_env_params: Any
    ) -> models.InfraEnv:
        """
        Create a new infrastructure environment.

        Args:
            name: The name of the infrastructure environment.
            **infra_env_params: Additional infrastructure environment parameters.

        Returns:
            models.InfraEnv: The created infrastructure environment object.
        """
        infra_env = models.InfraEnvCreateParams(
            name=name, pull_secret=self.pull_secret, **infra_env_params
        )
        log.info("Creating infra-env with params %s", infra_env.__dict__)
        result = await asyncio.to_thread(
            self._installer_api().register_infra_env, infraenv_create_params=infra_env
        )
        return cast(models.InfraEnv, result)

    async def update_cluster(
        self,
        cluster_id: str,
        api_vip: Optional[str] = "",
        ingress_vip: Optional[str] = "",
        **update_params: Any,
    ) -> models.Cluster:
        """
        Update cluster configuration.

        Args:
            cluster_id: The unique identifier of the cluster to update.
            api_vip: Optional API virtual IP address.
            ingress_vip: Optional ingress virtual IP address.
            **update_params: Additional cluster update parameters.

        Returns:
            models.Cluster: The updated cluster object.
        """
        params = models.V2ClusterUpdateParams(**update_params)
        if api_vip != "":
            params.api_vips = [models.ApiVip(cluster_id=cluster_id, ip=api_vip)]
        if ingress_vip != "":
            params.ingress_vips = [
                models.IngressVip(cluster_id=cluster_id, ip=ingress_vip)
            ]

        log.info("Updating cluster %s with params %s", cluster_id, params)
        return cast(
            models.Cluster,
            await asyncio.to_thread(
                self._installer_api().v2_update_cluster,
                cluster_id=cluster_id,
                cluster_update_params=params,
            ),
        )

    async def install_cluster(self, cluster_id: str) -> models.Cluster:
        """
        Start the installation process for a cluster.

        Args:
            cluster_id: The unique identifier of the cluster to install.

        Returns:
            models.Cluster: The cluster object with updated installation status.
        """
        log.info("Installing cluster %s", cluster_id)
        return cast(
            models.Cluster,
            await asyncio.to_thread(
                self._installer_api().v2_install_cluster, cluster_id=cluster_id
            ),
        )

    async def get_openshift_versions(
        self, only_latest: bool
    ) -> models.OpenshiftVersions:
        """
        Get supported OpenShift versions.

        Args:
            only_latest: Whether to return only the latest versions.

        Returns:
            models.OpenshiftVersions: Object containing available OpenShift versions.
        """
        return cast(
            models.OpenshiftVersions,
            await asyncio.to_thread(
                self._versions_api().v2_list_supported_openshift_versions,
                only_latest=only_latest,
            ),
        )

    async def get_operator_bundles(self) -> list[dict[str, Any]]:
        """
        Get available operator bundles.

        Returns:
            list: A list of operator bundle dictionaries.
        """
        bundles = cast(
            list, await asyncio.to_thread(self._operators_api().v2_list_bundles)
        )
        return [bundle.to_dict() for bundle in bundles]

    async def add_operator_bundle_to_cluster(
        self, cluster_id: str, bundle_name: str
    ) -> models.Cluster:
        """
        Add an operator bundle to a cluster.

        Args:
            cluster_id: The unique identifier of the cluster.
            bundle_name: The name of the operator bundle to add.

        Returns:
            models.Cluster: The updated cluster object with the new operator.
        """
        bundle = cast(
            Any,
            await asyncio.to_thread(self._operators_api().v2_get_bundle, bundle_name),
        )
        olm_operators = [
            models.OperatorCreateParams(name=op_name) for op_name in bundle.operators
        ]
        return await self.update_cluster(
            cluster_id=cluster_id, olm_operators=olm_operators
        )

    async def update_host(
        self, host_id: str, infra_env_id: str, **update_params: Any
    ) -> models.Host:
        """
        Update host configuration within an infrastructure environment.

        Args:
            host_id: The unique identifier of the host to update.
            infra_env_id: The infrastructure environment ID containing the host.
            **update_params: Host update parameters.

        Returns:
            models.Host: The updated host object.
        """
        params = models.HostUpdateParams(**update_params)
        return cast(
            models.Host,
            await asyncio.to_thread(
                self._installer_api().v2_update_host, infra_env_id, host_id, params
            ),
        )
