import base64
import json
import os
import subprocess
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.cloud import container_v1, compute_v1
import google.auth
from kubernetes import config as kube_config
from app.config import Config
from flask import current_app
import time
import datetime
import logging

class ConnectToCustomerGCPDataPlatform:
    def __init__(self, customer, region, project_id=None, cloud_provider=None, access_token=None, refresh_token=None, token_expiry=None, token_key=None):
        self.logger = logging.getLogger(__name__)
        self.cloud_provider = cloud_provider or "gcp"
        self.customer = customer
        self.region = region
        self.project_id = project_id or f"fast-bi-{customer}"
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.token_key = token_key
        self.logger.info(f"Initializing ConnectToCustomerGCPDataPlatform for customer: {customer}")
        self.credentials = self.authenticate_gcp()
        self.cluster_name = self.get_cluster_name()
        self.kube_config_path = f'/tmp/fast-bi-{self.customer}-platform-kubeconfig.yaml'
        self.address_client = compute_v1.AddressesClient(credentials=self.credentials)

    def get_cluster_name(self):
        self.logger.info(f"Fetching cluster name starting with 'fast-bi-' in project {self.project_id} and region {self.region}")
        gke_client = container_v1.ClusterManagerClient(credentials=self.credentials)
        try:
            parent = f"projects/{self.project_id}/locations/{self.region}"
            response = gke_client.list_clusters(parent=parent)
            for cluster in response.clusters:
                if cluster.name.startswith("fast-bi-"):
                    self.logger.info(f"Found cluster: {cluster.name}")
                    return cluster.name
            self.logger.warning(f"No cluster found starting with 'fast-bi-' in {self.region}")
            return f"fast-bi-{self.customer}-platform"  # Fallback to default name
        except Exception as e:
            self.logger.error(f"Failed to fetch clusters: {str(e)}")
            return f"fast-bi-{self.customer}-platform"  # Fallback to default name

    def refresh_access_token_if_needed(self):
        if self.access_token and self.refresh_token:
            if self.is_token_expired():
                current_app.logger.info("Token is expired, attempting to refresh")
                try:
                    creds = Credentials.from_authorized_user_info(
                        {"refresh_token": self.refresh_token, "client_id": Config.CLIENT_ID, "client_secret": Config.CLIENT_SECRET},
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    creds.refresh(Request())
                    current_app.logger.info("Token refreshed successfully")
                    self.access_token = creds.token
                    
                    # Calculate new expiry
                    if creds.expiry:
                        self.token_expiry = creds.expiry.timestamp()
                    else:
                        # If expiry is not set, default to 1 hour from now
                        self.token_expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).timestamp()
                    
                    current_app.logger.info(f"New token expiry set to: {self.token_expiry}")
                    
                    # Update the token in the database
                    metadata_collector = current_app.metadata_collector
                    metadata_collector.save_token(self.token_key, self.access_token, self.refresh_token, self.token_expiry)
                    current_app.logger.info("Token updated in database")
                except Exception as e:
                    current_app.logger.error(f"Error refreshing token: {str(e)}")
            else:
                current_app.logger.info("Token is still valid, no refresh needed")
        else:
            current_app.logger.warning("No access token or refresh token available")

    def is_token_expired(self):
        if self.token_expiry is None:
            current_app.logger.info("Token expiry is None, considering as expired")
            return True
        current_time = time.time()
        is_expired = self.token_expiry <= current_time + 300
        current_app.logger.info(f"Token expiry: {datetime.datetime.fromtimestamp(self.token_expiry)}, "
                    f"Current time: {datetime.datetime.fromtimestamp(current_time)}, "
                    f"Is expired: {is_expired}")
        return is_expired

    def authenticate_gcp(self):
        self.logger.info("Authenticating with Google Cloud")
        self.refresh_access_token_if_needed()
        if self.access_token:
            self.logger.info("Using provided access token for authentication")
            credentials = Credentials(self.access_token)
        else:
            self.logger.info("Using default credentials")
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        
        if credentials.expired:
            self.logger.info("Refreshing expired credentials")
            credentials.refresh(Request())
        return credentials

    def get_kubernetes_credentials(self):
        self.logger.info("Getting Kubernetes credentials")
        self.refresh_access_token_if_needed()
        gke_client = container_v1.ClusterManagerClient(credentials=self.credentials)
        try:
            cluster = gke_client.get_cluster(
                name=f'projects/{self.project_id}/locations/{self.region}/clusters/{self.cluster_name}'
            )
            self.logger.info(f"Successfully retrieved cluster information for {self.cluster_name}")
            self.configure_kubectl(cluster)
        except Exception as e:
            self.logger.error(f"Failed to get cluster information: {str(e)}")
            raise

    def configure_kubectl(self, cluster):
        self.logger.info("Configuring kubectl")
        kube_config_content = self.generate_kube_config(cluster)
        with open(self.kube_config_path, 'w') as f:
            f.write(kube_config_content)
        os.chmod(self.kube_config_path, 0o600)  # Secure the kubeconfig file
        os.environ['KUBECONFIG'] = self.kube_config_path
        kube_config.load_kube_config(config_file=self.kube_config_path)
        self.logger.info(f"kubectl configuration saved to {self.kube_config_path}")

    def generate_kube_config(self, cluster):
        self.logger.info("Generating kube config")
        ca_cert_path = self.save_ca_cert(cluster.master_auth.cluster_ca_certificate)
        token = self.credentials.token
        config_content = f"""
apiVersion: v1
kind: Config
clusters:
- name: {self.cluster_name}
  cluster:
    server: https://{cluster.endpoint}
    certificate-authority: {ca_cert_path}
contexts:
- name: {self.cluster_name}
  context:
    cluster: {self.cluster_name}
    user: {self.cluster_name}
users:
- name: {self.cluster_name}
  user:
    token: {token}
current-context: {self.cluster_name}
"""
        self.logger.info("Kube config generated successfully")
        return config_content

    def save_ca_cert(self, ca_cert):
        self.logger.info("Saving CA certificate")
        ca_cert_decoded = base64.b64decode(ca_cert).decode('utf-8')
        ca_path = f'/tmp/{self.cluster_name}-ca.crt'
        with open(ca_path, 'w') as ca_file:
            ca_file.write(ca_cert_decoded)
        self.logger.info(f"CA certificate saved to {ca_path}")
        return ca_path

    def test_kubernetes_connection(self):
        self.logger.info("Testing Kubernetes connection")
        try:
            command = ["kubectl", "get", "nodes", "--kubeconfig", self.kube_config_path]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.logger.info(f"Successfully connected to Kubernetes. Output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to connect to Kubernetes: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error while testing Kubernetes connection: {str(e)}")
            return False

    def fetch_external_ip(self, address_name):
        self.logger.info(f"Fetching external IP for {address_name}")
        self.refresh_access_token_if_needed()
        try:
            address = self.address_client.get(
                project=self.project_id,
                region=self.region,
                address=address_name
            )
            ip_address = address.address
            if not ip_address:
                raise Exception(f"No external IP address found for {address_name} in project {self.project_id}.")
            self.logger.info(f"External IP fetched successfully: {ip_address}")
            return ip_address
        except Exception as e:
            self.logger.error(f"Failed to fetch external IP: {str(e)}")
            raise


class ConnectToCustomerAWSDataPlatform: ##TODO: Not finished of AWS Connecto to ECK class.
    def __init__(self, customer, region, project_id=None, cloud_provider=None):
        #Service specific tf - Basic
        self.cloud_provider = cloud_provider if cloud_provider else "gcp"
        self.customer = customer
        self.region = region
        self.project_id = project_id if project_id else f"fast-bi-{customer}"
        self.cluster_name = f"fast-bi-{self.customer}-platform"

    def aws_eck_connect(self):
        return True
    
class ConnectToCustomerAzureDataPlatform: ##TODO: Not finished of Azure Connecto to ACK class.
    def __init__(self, customer, region, project_id=None, cloud_provider=None):
        #Service specific tf - Basic
        self.cloud_provider = cloud_provider if cloud_provider else "gcp"
        self.customer = customer
        self.region = region
        self.project_id = project_id if project_id else f"fast-bi-{customer}"
        self.cluster_name = f"fast-bi-{self.customer}-platform"

    def azure_ack_connect(self):
        return True