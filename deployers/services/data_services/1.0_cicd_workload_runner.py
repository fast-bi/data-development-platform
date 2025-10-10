#TODO: Add support for github, not tested yet
#TODO: Add support for gitea, not tested yet
#TODO: Add support for bitbucket, not tested yet

import subprocess
import os
from datetime import datetime
import json
import requests
import logging
import sys
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('cicd_workload_runner_deployer')

class Platformk8sGitRunner:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name, git_provider=None,
                 method="local_vault", external_infisical_host=None, slug=None, vault_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None, git_runner_access_token=None, git_runner_private_key=None, git_repo=None,
                 git_provider_url=None, project_id=None, cluster_name=None, kube_config_path=None,
                 namespace="cicd-workload-trigger"):
        self.deployment_environment = "data-services"
        self.external_infisical_host = external_infisical_host
        self.namespace = namespace
        self.project_slug = slug
        self.vault_project_id = vault_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.customer = customer
        self.domain_name = domain_name
        self.cloud_provider = cloud_provider
        self.metadata_collector = metadata_collector
        self.git_provider = git_provider
        self.git_repo = git_repo
        self.git_provider_url = git_provider_url if git_provider_url else self._extract_git_provider_url(git_repo) if git_repo else "https://gitlab.fast.bi"
        self.git_runner_access_token = git_runner_access_token
        self.git_runner_private_key = git_runner_private_key
        self.full_domain_name = f"{customer}.{domain_name}"
        self.ingress_host = f"gitwebhook.{self.full_domain_name}"

        # Validate method and required parameters
        if method not in ["local_vault", "external_infisical"]:
            raise ValueError(f"Unsupported method: {method}")
        self.method = method
        
        # Validate method-specific requirements
        if method == "external_infisical":
            if not all([slug, vault_project_id, secret_manager_client_id, secret_manager_client_secret]):
                raise ValueError("slug, vault_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
        elif method == "local_vault":
            self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")
        
        # Chart configuration Global
        self.chart_version = chart_version
        self.deployment_name = "fastbi-cicd-trigger-runner"
        self.values_path = "charts/data_services_charts/cicd_workload_runner/values.yaml"
        self.values_extra_path = "charts/data_services_charts/cicd_workload_runner/values_extra.yaml"

        # Extra values file chart configuration
        self.extra_chart_version = "0.1.1"
        self.extra_deployment_name = "fastbi-cicd-trigger-runner-extra"
        self.extra_chart_repo_name = "kube-core"
        self.extra_chart_repo = "https://kube-core.github.io/helm-charts"
        self.extra_chart_name = "kube-core/raw"
        self.extra_render_template_values_extra_path = "charts/data_services_charts/cicd_workload_runner/values_extra.yaml"
        
        # Git Provider Specific
        if not self.git_provider:
            self.git_provider = self._detect_git_provider(self.git_provider_url)
            
        if self.git_provider == "fastbi":
            self.chart_repo_name = "gitlab"
            self.chart_repo = "https://charts.gitlab.io/"
            self.chart_name = "gitlab/gitlab-runner"
            self.render_template_values_path = "charts/data_services_charts/cicd_workload_runner/gitlab/template_gitlab_values.yaml"
            self.render_template_values_extra_path = "charts/data_services_charts/cicd_workload_runner/gitlab/template_gitlab_values_extra.yaml"
        elif self.git_provider == "gitlab":
            self.chart_repo_name = "gitlab"
            self.chart_repo = "https://charts.gitlab.io/"
            self.chart_name = "gitlab/gitlab-runner"
            self.render_template_values_path = "charts/data_services_charts/cicd_workload_runner/gitlab/template_gitlab_values.yaml"
            self.render_template_values_extra_path = "charts/data_services_charts/cicd_workload_runner/gitlab/template_gitlab_values_extra.yaml"
        elif self.git_provider == "github":
            self.chart_repo_name = "github"
            self.chart_repo = "https://actions-runner-controller.github.io/actions-runner-controller"
            self.chart_name = "actions-runner-controller/actions-runner-controller"
            self.render_template_values_path = "charts/data_services_charts/cicd_workload_runner/github/template_github_values.yaml"
            self.render_template_values_extra_path = "charts/data_services_charts/cicd_workload_runner/github/template_github_values_extra.yaml"
        elif self.git_provider == "gitea":
            self.chart_repo_name = "gitea"
            self.chart_repo = "https://gitea.com/marketplace/actions/gitea-actions-runner-controller"
            self.chart_name = "gitea-actions-runner-controller/gitea-actions-runner-controller"
            self.render_template_values_path = "charts/data_services_charts/cicd_workload_runner/gitea/template_gitea_values.yaml"
            self.render_template_values_extra_path = "charts/data_services_charts/cicd_workload_runner/gitea/template_gitea_values_extra.yaml"
        elif self.git_provider == "bitbucket":
            self.chart_repo_name = "bitbucket"
            self.chart_repo = "https://bitbucket.org/marketplace/actions/bitbucket-actions-runner-controller"
            self.chart_name = "bitbucket-actions-runner-controller/bitbucket-actions-runner-controller"
            self.render_template_values_path = "charts/data_services_charts/cicd_workload_runner/bitbucket/template_bitbucket_values.yaml"
            self.render_template_values_extra_path = "charts/data_services_charts/cicd_workload_runner/bitbucket/template_bitbucket_values_extra.yaml"
        else:
            raise ValueError(f"Unsupported git provider: {self.git_provider}")

        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                self.project_id = project_id if project_id else f"fast-bi-{customer}"
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for Azure with cluster: {self.cluster_name}")
            elif self.cloud_provider == "self-managed":
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for self-managed with cluster: {self.cluster_name}")
            else:
                raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
        except Exception as e:
            logger.error(f"Error during cloud provider configuration: {str(e)}")
            raise
            
        # Set kubeconfig path after cluster_name is properly initialized
        self.kube_config = kube_config_path if kube_config_path else f'/tmp/{self.cluster_name}-kubeconfig.yaml'
        logger.info(f"Using kubeconfig: {self.kube_config}")
        
        # Check if kubeconfig exists
        if not os.path.exists(self.kube_config):
            logger.warning(f"Kubeconfig file not found at {self.kube_config}. Deployment may fail.")
        
        # MetadataCollection
        self.app_name = self.chart_name.split('/')[1]
        
        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.render_template_values_path,
            self.render_template_values_extra_path
        ]
        for path in required_paths:
            template_path = Path(path)
            if not template_path.exists():
                logger.error(f"Template file not found: {template_path}")
                raise FileNotFoundError(f"Template file not found: {template_path}")
            logger.debug(f"Template file validated: {template_path}")

    def deploy_service(self, chart_repo_name, chart_repo, deployment_name, chart_name, chart_version, namespace, values_path):
        """Deploy a Helm chart service"""
        logger.info(f"Deploying {deployment_name} in namespace {namespace}")
        
        # Check if values file exists
        if not os.path.exists(values_path):
            logger.error(f"Values file not found: {values_path}")
            raise FileNotFoundError(f"Values file not found: {values_path}")
            
        try:
            # Properly add and update the Helm repo
            self.execute_command(["helm", "repo", "add", chart_repo_name, chart_repo])
            self.execute_command(["helm", "repo", "update", chart_repo_name])
            
            # Formulate the Helm upgrade command properly as a list
            helm_command = [
                "helm", "upgrade", "-i", deployment_name, chart_name,
                "--version", chart_version,
                "--namespace", namespace,
                "--create-namespace",
                "--values", values_path,
                "--kubeconfig", self.kube_config
            ]
            self.execute_command(helm_command)
            logger.info(f"Successfully deployed {deployment_name} in namespace {namespace}")
        except Exception as e:
            logger.error(f"Failed to deploy {deployment_name}: {str(e)}")
            raise

    def get_deployed_app_version(self, deployment_name, namespace):
        """Get the deployed application version from Helm"""
        logger.info(f"Getting deployed version for {deployment_name} in namespace {namespace}")
        try:
            command = ["helm", "ls", "--deployed", "-f", deployment_name, "-n", namespace, "--kubeconfig", self.kube_config, "--output", "json"]
            result = self.execute_command(command)
            if result:
                # Parse JSON output
                deployments = json.loads(result)
                if deployments and isinstance(deployments, list) and len(deployments) > 0:
                    app_version = deployments[0].get('app_version', "Unknown")
                    logger.info(f"Found app version: {app_version}")
                    return app_version
                else:
                    logger.warning(f"No deployments found for {deployment_name}")
            return "No deployed version found"
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Helm output as JSON: {str(e)}")
            return "Error parsing version"
        except Exception as e:
            logger.error(f"Error getting deployed version: {str(e)}")
            return "Error getting version"

    def execute_command(self, command):
        """Execute a shell command with proper error handling"""
        cmd_str = ' '.join(command)
        logger.debug(f"Executing command: {cmd_str}")
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.debug(f"Command output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd_str}")
            logger.error(f"Status code: {e.returncode}")
            logger.error(f"Output: {e.stdout}")
            logger.error(f"Error: {e.stderr}")
            raise Exception(f"Execution failed for command {cmd_str}: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error executing command {cmd_str}: {str(e)}")
            raise

    def authenticate_with_vault(self):
        """Authenticate with the vault and return an access token."""
        if self.method != "external_infisical":
            return None
            
        logger.info("Authenticating with external Infisical vault")
        try:
            auth_url = f"{self.external_infisical_host}/api/v1/auth/universal-auth/login"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                "clientId": self.secret_manager_client_id,
                "clientSecret": self.secret_manager_client_secret
            }
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()['accessToken']
        except Exception as e:
            logger.error(f"Failed to authenticate with vault: {str(e)}")
            raise

    def get_secret_from_vault(self, secret_name, secret_path, access_token=None, environment="prod", version=None, secret_type="shared", include_imports="false"):
        """Retrieve the secret from the vault using the appropriate method."""
        if self.method == "external_infisical":
            return self._get_secret_from_external_vault(
                secret_name, secret_path, access_token, environment, version, secret_type, include_imports
            )
        else:
            return self._get_secret_from_local_vault(secret_name, secret_path)

    def _get_secret_from_external_vault(self, secret_name, secret_path, access_token, environment, version, secret_type, include_imports):
        """Retrieve the secret from the external Infisical vault."""
        try:
            url = f"{self.external_infisical_host}/api/v3/secrets/raw/{secret_name}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "workspaceId": self.vault_project_id,
                "environment": environment,
                "secretPath": secret_path,
                "version": version,
                "type": secret_type,
                "include_imports": include_imports
            }
            params = {k: v for k, v in params.items() if v is not None}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()['secret']['secretValue']
        except Exception as e:
            logger.error(f"Failed to get secret from external vault: {str(e)}")
            raise

    def _get_secret_from_local_vault(self, secret_name, secret_path):
        """Retrieve the secret from the local vault JSON file."""
        try:
            with open(self.secret_file, 'r') as f:
                vault_data = json.load(f)
            
            # Navigate through the JSON structure based on the secret path
            current = vault_data
            for part in secret_path.strip('/').split('/'):
                if part not in current:
                    raise KeyError(f"Path {secret_path} not found in vault structure")
                current = current[part]
            
            if secret_name not in current:
                raise KeyError(f"Secret {secret_name} not found at path {secret_path}")
            
            return current[secret_name]
        except Exception as e:
            logger.error(f"Failed to get secret from local vault: {str(e)}")
            raise

    def render_values_file(self, git_runner_token, git_runner_private_key, git_repo):
        """Render the values file from template"""
        logger.info("Rendering values file from template")
        try:
            context = {
                'chart_name': self.chart_name,
                'chart_repo': self.chart_repo,
                'chart_version': self.chart_version,
                'git_runner_token': git_runner_token,
                'git_runner_private_key': git_runner_private_key,
                'git_provider_url': self.git_provider_url,
                'ingress_host': self.ingress_host,
                'git_repo': git_repo,
                'method': self.method,
                'secret_manager_client_id': self.secret_manager_client_id,
                'secret_manager_client_secret': self.secret_manager_client_secret,
                'external_infisical_host': self.external_infisical_host,
                'project_slug': self.project_slug,
                'domain_name': self.domain_name,
                'cloud_provider': self.cloud_provider
            }
            
            logger.info(f"Using git provider URL: {self.git_provider_url}")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            self.render_template(self.render_template_values_path, self.values_path, context)
            self.render_template(self.render_template_values_extra_path, self.values_extra_path, context)
            logger.info("Successfully rendered values files")
        except Exception as e:
            logger.error(f"Failed to render values file: {str(e)}")
            raise

    def render_template(self, template_path, output_path, context):
        """Render a template file with the given context"""
        try:
            logger.debug(f"Rendering template {template_path} to {output_path}")
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))
            output = template.render(context)
            with open(output_path, 'w') as f:
                f.write(output)
            logger.debug("Template rendered successfully")
        except TemplateNotFound as e:
            logger.error(f"Template not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
            raise

    def run(self):
        """Main execution method"""
        logger.info(f"Starting CICD Workload Runner deployment for customer: {self.customer}")
        try:
            # Get secrets from vault
            access_token = self.authenticate_with_vault()
            
            if self.git_runner_access_token:
                git_runner_token = self.git_runner_access_token
            else:
                # Get git runner token from vault
                git_runner_token = self.get_secret_from_vault(
                    secret_name="RUNNER-REGISTRATION-TOKEN",
                    secret_path="/data-platform-runner/ci-access-tokens/",
                    access_token=access_token
                )

            if self.git_runner_private_key:
                git_runner_private_key = self.git_runner_private_key
            else:
                # Get git runner private key from vault
                git_runner_private_key = self.get_secret_from_vault(
                    secret_name="private",
                    secret_path="/data-platform-runner/ssh-keys-data-model-repo/",
                    access_token=access_token
                )
            
            if self.git_repo:
                git_repo = self.git_repo
            else:
                # Get git repo from vault
                git_repo = self.get_secret_from_vault(
                    secret_name="data_repo_url",
                    secret_path="/data-platform-runner/git_provider_repo_urls/",
                    access_token=access_token
                )
                
            # Update git provider URL based on the repository URL
            self.git_provider_url = self._extract_git_provider_url(git_repo)
            
            # Extract the repository name from the URL, remove http://, https://, and .git
            if self.git_provider == "github":
                # For GitHub (including Enterprise), extract the path after the domain
                # Remove protocol and .git suffix, then extract the path
                clean_url = git_repo.replace("http://", "").replace("https://", "").replace(".git", "")
                # Split by '/' and remove the domain part, keep the rest as org/repo
                url_parts = clean_url.split("/")
                if len(url_parts) >= 3:
                    git_repo_extact = "/".join(url_parts[1:])  # Skip domain, keep org/repo
                else:
                    git_repo_extact = clean_url
            else:
                git_repo_extact = git_repo.split("/")[-1].replace("http://", "").replace("https://", "").replace(".git", "")

            # Render and deploy
            self.render_values_file(git_runner_token=git_runner_token, git_runner_private_key=git_runner_private_key, git_repo=git_repo_extact)
            
            # Deploy service
            logger.info("Deploying CICD workload runner service")
            self.deploy_service(
                chart_repo_name=self.chart_repo_name,
                chart_repo=self.chart_repo,
                deployment_name=self.deployment_name,
                chart_name=self.chart_name,
                chart_version=self.chart_version,
                namespace=self.namespace,
                values_path=self.values_path
            )

            # Deploy extra resources
            if self.git_provider == "github":
                self.execute_command([
                    "kubectl", "wait", "--for=condition=ready", "pod",
                    "-l", "fastbi=cicd-workload-runner",
                    "-n", self.namespace,
                    "--timeout=300s",
                    "--kubeconfig", self.kube_config
                ])
                logger.info("Deploying CICD workload runner extra resources")
                self.deploy_service(
                    chart_repo_name=self.extra_chart_repo_name,
                    chart_repo=self.extra_chart_repo,
                    deployment_name=self.extra_deployment_name,
                    chart_name=self.extra_chart_name,
                    chart_version=self.extra_chart_version,
                    namespace=self.namespace,
                    values_path=self.values_extra_path
                )

            # Metadata Collection
            app_version = self.get_deployed_app_version(self.deployment_name, self.namespace)
            deployment_record = {
                "customer": self.customer,
                "customer_main_domain": f"{self.customer}.fast.bi",
                "customer_vault_slug": self.project_slug,
                "deployment_environment": self.deployment_environment,
                "deployment_name": self.deployment_name,
                "chart_name": self.chart_name,
                "chart_version": self.chart_version,
                "app_name": self.app_name,
                "app_version": app_version,
                "deploy_date": datetime.now().strftime("%Y-%m-%d"),
                "domain_name": self.domain_name,
                "cloud_provider": self.cloud_provider,
                "method": self.method
            }
            
            logger.info("Adding deployment record to metadata collector")
            self.metadata_collector.add_deployment_record(deployment_record)
            logger.info("CICD Workload Runner deployment completed successfully")
            return "CICD Workload Runner deployed successfully"
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create an instance from CLI arguments."""
        return cls(
            chart_version=args.chart_version,
            customer=args.customer,
            metadata_collector=args.metadata_collector,
            cloud_provider=args.cloud_provider,
            domain_name=args.domain_name,
            method=args.method,
            external_infisical_host=args.external_infisical_host,
            slug=args.slug,
            vault_project_id=args.vault_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            git_runner_access_token=args.git_runner_token,
            git_runner_private_key=args.git_runner_private_key,
            git_repo=args.git_repo,
            git_provider=args.git_provider,
            git_provider_url=args.git_url,
            project_id=args.project_id,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            namespace=args.namespace
        )

    def _extract_git_provider_url(self, git_repo_url):
        """Extract the git provider URL from the git repository URL."""
        if not git_repo_url:
            return "https://gitlab.fast.bi"
            
        # Remove .git suffix if present
        url = git_repo_url.replace(".git", "")
        
        # Extract the base URL (protocol + domain)
        if url.startswith("http://") or url.startswith("https://"):
            # Split by / and take the first two parts (protocol and domain)
            parts = url.split("/")
            if len(parts) >= 3:
                return f"{parts[0]}//{parts[2]}"
        
        return "https://gitlab.fast.bi"
        
    def _detect_git_provider(self, git_provider_url):
        """Detect the git provider based on the provider URL."""
        if not git_provider_url:
            return "fastbi"
            
        url = git_provider_url.lower()
        
        if "gitlab" in url:
            return "gitlab"
        elif "github" in url:
            return "github"
        elif "gitea" in url:
            return "gitea"
        elif "bitbucket" in url:
            return "bitbucket"
        else:
            return "fastbi"

def main():
    # Configure file logging if running as main script
    log_file = "cicd_workload_runner_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting CICD Workload Runner deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="CICD Workload Runner Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Method group
    method_group = parser.add_argument_group('vault method')
    method_group.add_argument(
        '--method',
        choices=['external_infisical', 'local_vault'],
        default='local_vault',
        help='Vault method to use. Choose between external Infisical service or local HashiCorp vault'
    )
    method_group.add_argument(
        '--external_infisical_host',
        help='External Infisical host (required if method is external_infisical)'
    )
    method_group.add_argument(
        '--slug',
        help='Project slug for the vault (required for local_vault method)'
    )
    method_group.add_argument(
        '--vault_project_id',
        help='Vault project ID (required for external_infisical method)'
    )
    method_group.add_argument(
        '--client_id',
        help='Secret manager client ID (required for external_infisical method)'
    )
    method_group.add_argument(
        '--client_secret',
        help='Secret manager client secret (required for external_infisical method)'
    )

    # Required core arguments
    required_args = parser.add_argument_group('required core arguments')
    required_args.add_argument(
        '--customer',
        required=True,
        help='Customer tenant name (lowercase letters, numbers, and hyphens only)'
    )
    required_args.add_argument(
        '--chart_version',
        required=True,
        help='Chart version for CICD Workload Runner'
    )
    required_args.add_argument(
        '--cloud_provider',
        required=True,
        choices=['gcp', 'aws', 'azure', 'self-managed'],
        help='Cloud provider where the cluster is running'
    )
    required_args.add_argument(
        '--domain_name',
        required=True,
        help='Domain name for the customer'
    )

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--project_id',
        help='Cloud provider project ID (default: fast-bi-{customer})'
    )
    optional_args.add_argument(
        '--cluster_name',
        help='Kubernetes cluster name (default: fast-bi-{customer}-platform)'
    )
    optional_args.add_argument(
        '--kube_config_path',
        help='Path to kubeconfig file (default: /tmp/{cluster_name}-kubeconfig.yaml)'
    )
    optional_args.add_argument(
        '--namespace',
        default='cicd-workload-trigger',
        help='Kubernetes namespace for deployment (default: cicd-workload-trigger)'
    )
    optional_args.add_argument(
        '--metadata_file',
        default='deployment_metadata.json',
        help='Path to metadata file (default: deployment_metadata.json)'
    )
    optional_args.add_argument(
        '--skip_metadata',
        action='store_true',
        help='Skip metadata collection (for CLI usage)'
    )
    optional_args.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    # Git-specific arguments
    git_args = parser.add_argument_group('git configuration')
    git_args.add_argument(
        '--git_provider',
        default='fastbi',
        choices=['fastbi', 'github', 'gitlab', 'gitea', 'bitbucket'],
        help='Git provider to use (default: fastbi)'
    )
    git_args.add_argument(
        '--git_repo',
        help='Git repository URL (optional, will be retrieved from vault if not provided)'
    )
    git_args.add_argument(
        '--git_url',
        help='Git provider URL (optional, will be extracted from git_repo if not provided)'
    )
    git_args.add_argument(
        '--git_runner_token',
        help='Git runner token (optional, will be retrieved from vault if not provided)'
    )
    git_args.add_argument(
        '--git_runner_private_key',
        help='Git runner private key (optional, will be retrieved from vault if not provided)'
    )

    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Create metadata collector based on skip_metadata flag
    # Create a simple metadata collector for CLI usage
    class SimpleMetadataCollector:
        def __init__(self, metadata_file):
            self.metadata_file = metadata_file
            self.deployment_records = []
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        self.deployment_records = json.load(f)
                        logger.info(f"Loaded {len(self.deployment_records)} existing deployment records")
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse {metadata_file}, starting with empty records")
                    self.deployment_records = []
            else:
                logger.info(f"Metadata file {metadata_file} not found, will create new file")
        
        def add_deployment_record(self, record):
            self.deployment_records.append(record)
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(self.metadata_file)), exist_ok=True)
                with open(self.metadata_file, 'w') as f:
                    json.dump(self.deployment_records, f, indent=2)
                logger.info(f"Deployment record added to {self.metadata_file}")
            except Exception as e:
                logger.error(f"Failed to write metadata to {self.metadata_file}: {str(e)}")

    # Use the appropriate metadata collector
    if args.skip_metadata:
        logger.info("Metadata collection is disabled")
        class DummyMetadataCollector:
            def add_deployment_record(self, record):
                logger.info("Metadata collection skipped")
        metadata_collector = DummyMetadataCollector()
    else:
        logger.info(f"Using metadata file: {args.metadata_file}")
        metadata_collector = SimpleMetadataCollector(args.metadata_file)
    
    # Add metadata collector to args for from_cli_args method
    args.metadata_collector = metadata_collector
    
    try:
        # Initialize the CICD Workload Runner
        logger.info(f"Initializing CICD Workload Runner for customer {args.customer}")
        runner = Platformk8sGitRunner.from_cli_args(args)
        
        # Deploy the CICD Workload Runner
        logger.info("Starting CICD Workload Runner deployment")
        result = runner.run()
        logger.info("CICD Workload Runner deployment completed successfully")
        print("Execution Result:")
        print(result)
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        print(f"File not found error: {str(e)}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid value error: {str(e)}")
        print(f"Invalid value error: {str(e)}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command execution failed: {str(e)}")
        print(f"Command execution failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        print(f"Deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
