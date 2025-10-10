import subprocess
import logging

logger = logging.getLogger(__name__)

class CustomerSecretManagerSync:
    def __init__(self, customer, project_id=None, cluster_name=None, kube_config_path=None):
        self.deployment_environment = ["data-services", "infra-services"]
        self.customer = customer
        self.project_id = project_id if project_id else f"fast-bi-{customer}"
        self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
        self.kube_config = kube_config_path if kube_config_path else f'/tmp/{self.cluster_name}-kubeconfig.yaml'

    def execute_command(self, command):
        try:
            logger.info(f"Executing command: {' '.join(command)}")
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.cmd}")
            logger.error(f"Status code: {e.returncode}")
            logger.error(f"Output: {e.stdout}")
            logger.error(f"Error: {e.stderr}")
            raise Exception(f"Execution failed for command {' '.join(command)}: {e.stderr}")

    def get_namespaces(self):
        command = [
            "kubectl", "get", "namespaces",
            "-o", "jsonpath={.items[*].metadata.name}",
            "--kubeconfig", self.kube_config
        ]
        result = self.execute_command(command)
        return result.split()

    def get_infisical_secrets(self, namespace):
        command = [
            "kubectl", "get", "infisicalsecrets",
            "-n", namespace,
            "-o", "jsonpath={.items[*].metadata.name}",
            "--kubeconfig", self.kube_config
        ]
        result = self.execute_command(command)
        return result.split()

    def update_resync_interval(self, namespace, secret_name, new_interval):
        patch_command = [
            "kubectl", "patch", "infisicalsecret", secret_name,
            "-n", namespace,
            "--type", "json",
            "-p", f'[{{"op": "replace", "path": "/spec/resyncInterval", "value": {new_interval}}}]',
            "--kubeconfig", self.kube_config
        ]
        self.execute_command(patch_command)

    def update_all_infisical_secrets(self, new_interval=86400):
        logger.info("Starting update process for all InfisicalSecret resources")
        namespaces = self.get_namespaces()
        
        for namespace in namespaces:
            logger.info(f"Processing namespace: {namespace}")
            infisical_secrets = self.get_infisical_secrets(namespace)
            
            for secret in infisical_secrets:
                logger.info(f"Updating InfisicalSecret {secret} in namespace {namespace}")
                try:
                    self.update_resync_interval(namespace, secret, new_interval)
                    logger.info(f"Successfully updated {secret} in namespace {namespace}")
                except Exception as e:
                    logger.error(f"Failed to update {secret} in namespace {namespace}: {str(e)}")

        logger.info("Update process completed")

    def run(self):
        logger.info("Starting CustomerSecretManagerSync process")
        self.update_all_infisical_secrets()
        logger.info("CustomerSecretManagerSync process completed")