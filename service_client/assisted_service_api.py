import base64
import json
import os
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests
from assisted_service_client import ApiClient, Configuration, api, models
from retry import retry

from service_client.logger import log

class InventoryClient(object):
    def __init__(
        self,
        offline_token: Optional[str],
    ):
        self.inventory_url = "https://api.openshift.com/api/assisted-install/v2"
        configs = Configuration()
        configs.host = self.get_host(configs)
        configs.debug = True
        self.set_config_auth(c=configs, offline_token=offline_token)

        self.api = ApiClient(configuration=configs)
        self.client = api.InstallerApi(api_client=self.api)
        self.events = api.EventsApi(api_client=self.api)
        self.operators = api.OperatorsApi(api_client=self.api)

    def get_host(self, configs: Configuration) -> str:
        parsed_host = urlparse(configs.host)
        parsed_inventory_url = urlparse(self.inventory_url)
        return parsed_host._replace(netloc=parsed_inventory_url.netloc, scheme=parsed_inventory_url.scheme).geturl()

    @classmethod
    def set_config_auth(
        cls,
        c: Configuration,
        offline_token: Optional[str],
    ) -> None:

        @retry(exceptions=requests.HTTPError, tries=5, delay=5)
        def refresh_api_key(config: Configuration) -> None:
            # Get the properly padded key segment
            auth = config.api_key.get("Authorization", None)
            if auth is not None:
                segment = auth.split(".")[1]
                padding = len(segment) % 4
                segment = segment + padding * "="

                expires_on = json.loads(base64.b64decode(segment))["exp"]

                # if this key doesn't expire or if it has more than 10 minutes left, don't refresh
                remaining = expires_on - time.time()
                if expires_on == 0 or remaining > 600:
                    return

            log.info("Refreshing API key")

            params = {
                "client_id": "cloud-services",
                "grant_type": "refresh_token",
                "refresh_token": offline_token,
            }

            sso_url = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
            response = requests.post(sso_url, data=params)
            response.raise_for_status()

            config.api_key["Authorization"] = response.json()["access_token"]

        c.api_key_prefix["Authorization"] = "Bearer"
        c.refresh_api_key_hook = refresh_api_key

    def get_cluster_hosts(self, cluster_id: str, get_unregistered_clusters: bool = False) -> List[Dict[str, Any]]:
        cluster_details = self.cluster_get(cluster_id, get_unregistered_clusters=get_unregistered_clusters)
        return list(map(lambda host: host.to_dict(), cluster_details.hosts))

    def get_infra_env_hosts(self, infra_env_id: str) -> List[Dict[str, Any]]:
        return self.client.v2_list_hosts(infra_env_id=infra_env_id)

    def get_infra_env(self, infra_env_id: str) -> models.infra_env.InfraEnv:
        return self.client.get_infra_env(infra_env_id=infra_env_id)

    def get_cluster_operators(self, cluster_id: str) -> List[models.MonitoredOperator]:
        return self.cluster_get(cluster_id=cluster_id).monitored_operators

    def get_hosts_in_statuses(self, cluster_id: str, statuses: List[str]) -> List[dict]:
        hosts = self.get_cluster_hosts(cluster_id)
        return [host for host in hosts if host["status"] in statuses]

    def get_hosts_in_error_status(self, cluster_id: str):
        return self.get_hosts_in_statuses(cluster_id, ["error"])

    def clusters_list(self) -> List[Dict[str, Any]]:
        return self.client.v2_list_clusters()

    def infra_envs_list(self) -> List[Dict[str, Any]]:
        return self.client.list_infra_envs()

    def get_all_clusters(self) -> List[Dict[str, Any]]:
        return self.client.v2_list_clusters(get_unregistered_clusters=True)

    def get_cluster(self, cluster_id: str, get_unregistered_clusters: bool = False) -> models.cluster.Cluster:
        return self.client.v2_get_cluster(cluster_id=cluster_id, get_unregistered_clusters=get_unregistered_clusters)

    def get_infra_envs_by_cluster_id(self, cluster_id: str) -> List[Union[models.infra_env.InfraEnv, Dict[str, Any]]]:
        infra_envs = self.infra_envs_list()
        return [infra_env for infra_env in infra_envs if infra_env.get("cluster_id") == cluster_id]

    def get_hosts_id_with_macs(self, cluster_id: str) -> Dict[Any, List[str]]:
        hosts = self.get_cluster_hosts(cluster_id)
        hosts_data = {}
        for host in hosts:
            inventory = json.loads(host.get("inventory", '{"interfaces":[]}'))
            hosts_data[host["id"]] = [interface["mac_address"] for interface in inventory["interfaces"]]
        return hosts_data

    def get_host_by_mac(self, cluster_id: str, mac: str) -> Dict[str, Any]:
        hosts = self.get_cluster_hosts(cluster_id)

        for host in hosts:
            inventory = json.loads(host.get("inventory", '{"interfaces":[]}'))
            if mac.lower() in [interface["mac_address"].lower() for interface in inventory["interfaces"]]:
                return host

    def get_host_by_name(self, cluster_id: str, host_name: str) -> Dict[str, Any]:
        hosts = self.get_cluster_hosts(cluster_id)

        for host in hosts:
            hostname = host.get("requested_hostname")
            if hostname == host_name:
                log.info(f"Requested host by name: {host_name}, host details: {host}")
                return host

    def download_and_save_file(self, cluster_id: str, file_name: str, file_path: str) -> None:
        log.info("Downloading %s to %s", file_name, file_path)
        response = self.client.v2_download_cluster_files(
            cluster_id=cluster_id, file_name=file_name, _preload_content=False
        )
        with open(file_path, "wb") as _file:
            _file.write(response.data)

    def download_and_save_infra_env_file(self, infra_env_id: str, file_name: str, file_path: str) -> None:
        log.info(f"Downloading {file_name} to {file_path}")
        response = self.client.v2_download_infra_env_files(
            infra_env_id=infra_env_id, file_name=file_name, _preload_content=False
        )
        with open(os.path.join(file_path, f"{file_name}-{infra_env_id}"), "wb") as _file:
            _file.write(response.data)

    def download_host_ignition(self, infra_env_id: str, host_id: str) -> str:
        log.info("Downloading host %s infra_env %s ignition files to %s", host_id, infra_env_id, destination)

        response = self.client.v2_download_host_ignition(
            infra_env_id=infra_env_id, host_id=host_id, _preload_content=False
        )

        return response.data

    def get_events(
        self,
        cluster_id: Optional[str] = "",
        host_id: Optional[str] = "",
        infra_env_id: Optional[str] = "",
        categories=None,
        **kwargs,
    ) -> str:
        if categories is None:
            categories = ["user"]
        log.info("Downloading events for cluster %s, host %s, infraenv %s, categories %s", cluster_id, host_id, infra_env_id, categories)
        response = self.events.v2_list_events(
            cluster_id=cluster_id,
            host_id=host_id,
            infra_env_id=infra_env_id,
            categories=categories,
            _preload_content=False,
            **kwargs,
        )

        return response.data

    # TODO: maybe pull out only the error messages? Maybe with some context?
    def download_cluster_logs(self, cluster_id: str, output_file: str) -> None:
        log.info("Downloading cluster logs to %s", output_file)
        response = self.client.v2_download_cluster_logs(cluster_id=cluster_id, _preload_content=False)
        with open(output_file, "wb") as _file:
            _file.write(response.data)

    # TODO: maybe pull out only the error messages? Maybe with some context?
    def download_host_logs(self, cluster_id: str, host_id: str, output_file) -> None:
        log.info("Downloading host logs to %s", output_file)
        response = self.client.v2_download_cluster_logs(cluster_id=cluster_id, host_id=host_id, _preload_content=False)
        with open(output_file, "wb") as _file:
            _file.write(response.data)

    # TODO: ensure this is sanitized
    def get_cluster_install_config(self, cluster_id: str) -> str:
        log.info("Getting install-config for cluster %s", cluster_id)
        return self.client.v2_get_cluster_install_config(cluster_id=cluster_id)

    def get_discovery_ignition(self, infra_env_id: str) -> str:
        infra_env = self.get_infra_env(infra_env_id=infra_env_id)
        return infra_env.ingition_config_override
