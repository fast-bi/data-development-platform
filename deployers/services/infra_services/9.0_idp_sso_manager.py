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
import uuid
from flask import current_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('idp_sso_manager_deployer')

class IdpSsoManager:
    def __init__(self, chart_version, customer, metadata_collector, cloud_provider, domain_name,
                 method="local_vault", external_infisical_host=None, slug=None, secret_manager_project_id=None,
                 secret_manager_client_id=None, secret_manager_client_secret=None,
                 project_id=None, cluster_name=None, kube_config_path=None, 
                 namespace="sso-keycloak", dry_run=False):
        self.deployment_environment = "infrastructure"
        self.external_infisical_host = external_infisical_host
        self.namespace = namespace
        self.project_slug = slug
        self.secret_manager_project_id = secret_manager_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.customer = customer
        self.domain_name = domain_name
        self.cloud_provider = cloud_provider
        self.dry_run = dry_run
        #For local development
        self.local_postgresql = "false"
        
        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                if project_id and project_id.strip():
                    self.project_id = project_id
                    logger.info(f"Using provided project_id: {self.project_id}")
                else:
                    self.project_id = f"fast-bi-{customer}"
                    logger.warning(f"No project_id provided, using default: {self.project_id}")
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for GCP with project ID: {self.project_id}")
            elif self.cloud_provider == "aws":  # Leave for future clouds. Not supported yet
                self.project_id = None
                self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
                logger.info(f"Configured for AWS with cluster: {self.cluster_name}")
            elif self.cloud_provider == "azure":  # Leave for future clouds. Not supported yet
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

        self.metadata_collector = metadata_collector
        self.kube_config = kube_config_path if kube_config_path else f'/tmp/{self.cluster_name}-kubeconfig.yaml'
        
        # Validate method and required parameters
        if method not in ["local_vault", "external_infisical"]:
            raise ValueError(f"Unsupported method: {method}")
        self.method = method
        
        # Validate method-specific requirements
        if method == "external_infisical":
            if not all([secret_manager_project_id, secret_manager_client_id, secret_manager_client_secret]):
                raise ValueError("secret_manager_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
        elif method == "local_vault":
            self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")

        # Service specific
        self.chart_version = chart_version
        self.deployment_name = "idp-sso-manager"
        self.chart_repo_name = "bitnami"
        self.chart_name = "oci://registry-1.docker.io/bitnamicharts/keycloak"
        self.chart_repo = "https://charts.bitnami.com/bitnami"
        self.values_path = "charts/infra_services_charts/idp_sso_manager/values.yaml"
        self.render_template_values_path = "charts/infra_services_charts/idp_sso_manager/template_values.yaml"
        self.realm_template_path = "charts/infra_services_charts/idp_sso_manager/realm_teamplate.json"
        self.realm_path = f"charts/infra_services_charts/idp_sso_manager/{self.customer}_realm.json"
        self.customer_root_domain = f"{self.customer}.{self.domain_name}"
        self.ingress_host = f"login.{self.customer_root_domain}"
        
        # MetadataCollection
        self.app_name = self.chart_name.split('/')[1]
        
        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        required_paths = [
            self.render_template_values_path,
            self.realm_template_path
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
            # Properly add and update the Helm repo - Bitnami changed the chart name to oci://registry-1.docker.io/bitnamicharts/keycloak
            # self.execute_command(["helm", "repo", "add", chart_repo_name, chart_repo])
            # self.execute_command(["helm", "repo", "update", chart_repo_name])
            
            # Formulate the Helm upgrade command properly as a list
            helm_command = [
                "helm", "upgrade", "-i", deployment_name, chart_name,
                "--version", chart_version,
                "--namespace", namespace,
                "--create-namespace",
                "--wait",
                "--values", values_path,
                "--kubeconfig", self.kube_config,
                "--timeout", "15m"
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
        
        # Dry-run mode: show command without executing
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {cmd_str}")
            print(f"[DRY-RUN] Would execute: {cmd_str}")
            return ""  # Return mock success
        
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

    def render_values_file(self, database_name, database_username, root_username, replication_username, cloud_provider, project_slug ):
        """Render the values file from template"""
        logger.info("Rendering values file from template")
        try:
            context = {
                'chart_name': self.chart_name,
                'chart_repo': self.chart_repo,
                'chart_version': self.chart_version,
                'ingress_host': self.ingress_host,
                'database': database_name,
                'username': database_username,
                'adminUser': root_username,
                'replicationUsername': replication_username,
                'cloud_provider': cloud_provider,
                'method': self.method,
                'namespace': self.namespace,
                'project_slug': project_slug,
                'local_postgresql': self.local_postgresql
            }
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.values_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
                
            self.render_template(self.render_template_values_path, self.values_path, context)
            logger.info(f"Successfully rendered values file to {self.values_path}")
        except Exception as e:
            logger.error(f"Failed to render values file: {str(e)}")
            raise

    def render_realm_file(self, **client_configs):
        """Renders the realm configuration for Keycloak using the provided client details."""
        logger.info("Rendering realm file from template")
        try:
            # Log the client_configs to see what we're getting
            # logger.info("Client configs received:")
            # for key, value in client_configs.items():
            #     # Only log first few characters of sensitive values
            #     if 'secret' in key.lower():
            #         logger.info(f"{key}: {value[:5]}...")
            #     else:
            #         logger.info(f"{key}: {value}")

            context = {
                'realm_name': self.customer,
                'customer': self.customer,
                **client_configs
            }
            
            # # Log the final context
            # logger.info("Final context for template:")
            # for key, value in context.items():
            #     if 'secret' in key.lower():
            #         logger.info(f"{key}: {value[:5]}...")
            #     else:
            #         logger.info(f"{key}: {value}")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(self.realm_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
                
            self.render_template(self.realm_template_path, self.realm_path, context)
            logger.info(f"Successfully rendered realm file to {self.realm_path}")
            
            # Verify the file was created and has content
            if os.path.exists(self.realm_path):
                with open(self.realm_path, 'r') as f:
                    content = f.read()
                    logger.info(f"Realm file content length: {len(content)}")
                    logger.debug(f"Realm file content: {content}")
            else:
                logger.error(f"Realm file was not created at {self.realm_path}")
                
        except Exception as e:
            logger.error(f"Failed to render realm file: {str(e)}")
            raise

    def render_template(self, template_path, output_path, context):
        """Render a Jinja2 template to a file"""
        try:
            logger.debug(f"Rendering template {template_path} to {output_path}")
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))
            
            # # Log template variables
            # logger.info("Template variables:")
            # for key, value in context.items():
            #     if 'secret' in key.lower():
            #         logger.info(f"{key}: {value[:5]}...")
            #     else:
            #         logger.info(f"{key}: {value}")
            
            output = template.render(context)
            
            with open(output_path, 'w') as f:
                f.write(output)
            logger.debug("Template rendered successfully")
        except TemplateNotFound:
            logger.error(f"Template not found: {template_path}")
            raise FileNotFoundError(f"Template not found: {template_path}")
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
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
        # logger.info(f"Getting secret {secret_name} from external vault")
        try:
            url = f"{self.external_infisical_host}/api/v3/secrets/raw/{secret_name}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "workspaceId": self.secret_manager_project_id,
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
        # logger.info(f"Getting secret {secret_name} from local vault")
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

    def store_credentials(self, username, password):
        """Store credentials in cache and return a token."""
        try:
            # Try to use Flask's current_app.cache if in API context
            token = str(uuid.uuid4())
            current_app.cache.set(token, {'username': username, 'password': password}, timeout=3600)
            return token
        except RuntimeError:
            # If not in Flask context (CLI mode), return credentials directly
            logger.info("Running in CLI mode, returning credentials directly")
            return {
                'username': username,
                'password': password
            }

    def run(self):
        """Main execution method"""
        logger.info(f"Starting IDP SSO Manager deployment for customer: {self.customer}")
        try:
            # Get access token if using external vault
            access_token = self.authenticate_with_vault() if self.method == "external_infisical" else None
            
            # Get secrets based on method
            root_username = self.get_secret_from_vault(
                secret_name="adminUser",
                secret_path="/idp-sso/root-secrets/",
                access_token=access_token
            )
            root_password = self.get_secret_from_vault(
                secret_name="adminPassword",
                secret_path="/idp-sso/root-secrets/",
                access_token=access_token
            )
            database_name = self.get_secret_from_vault(
                secret_name="database",
                secret_path="/idp-sso/database-secrets/",
                access_token=access_token
            )
            database_username = self.get_secret_from_vault(
                secret_name="username",
                secret_path="/idp-sso/database-secrets/",
                access_token=access_token
            )
            replication_username = self.get_secret_from_vault(
                secret_name="replicationUsername",
                secret_path="/idp-sso/database-secrets/",
                access_token=access_token
            )
            # Get client secrets and render realm
            client_configs = self._get_client_configs(access_token)
            self.render_realm_file(**client_configs)

            # Render and deploy
            self.render_values_file(database_name, database_username, root_username, replication_username, self.cloud_provider, self.project_slug)
            self.deploy_service(
                chart_repo_name=self.chart_repo_name,
                chart_repo=self.chart_repo,
                deployment_name=self.deployment_name,
                chart_name=self.chart_name,
                chart_version=self.chart_version,
                namespace=self.namespace,
                values_path=self.values_path
            )
            
            # Metadata Collection
            app_version = self.get_deployed_app_version(self.deployment_name, self.namespace)
            deployment_record = {
                "customer": self.customer,
                "customer_main_domain": self.customer_root_domain,
                "customer_vault_slug": self.project_slug,
                "deployment_environment": self.deployment_environment,
                "deployment_name": self.deployment_name,
                "chart_name": self.chart_name,
                "chart_version": self.chart_version,
                "app_name": self.app_name,
                "app_version": app_version,
                "deploy_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            logger.info("Adding deployment record to metadata collector")
            self.metadata_collector.add_deployment_record(deployment_record)
            
            # Store credentials and return result
            credentials_result = self.store_credentials(root_username, root_password)
            logger.info("IDP SSO Manager deployment completed successfully")
            
            # Return appropriate response based on context
            if isinstance(credentials_result, dict):
                # CLI mode - return credentials directly
                return {
                    "message": "IDP SSO Manager deployed successfully.",
                    "credentials": credentials_result
                }
            else:
                # API mode - return token
                return {
                    "message": "IDP SSO Manager deployed successfully.",
                    "token": credentials_result
                }
            
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    def _get_client_configs(self, access_token):
        """Get all client configurations from the vault."""
        client_configs = {}
        
        # Define client configurations with their exact paths and redirect URLs
        clients = [
            ("data_cicd_workflows", "workflows", "/oauth2/callback", None),
            ("data_replication", "airbyte", "/oauth2/callback", None),
            ("data_orchestration", "airflow", "/oauth-authorized/FastBI-SSO", None),
            ("bi", None, None, None),
            ("data_catalog", "dc-auth", "/oauth2/callback", "/oauth2/sign_out"),
            ("data_quality", "dq-auth", "/oauth2/callback", "/oauth2/sign_out"),
            ("data_governance", "datahub", "/callback/oidc", None),
            ("data_modeling", "ide", "/hub/oauth_callback", None),
            ("platform_monitoring", "monitoring", "/login/generic_oauth", None),
            ("platform_object_storage", "minio", "/oauth_callback", None),
            ("user_console", None, "/oidc/callback", None)
        ]
        
        # Secret paths still use the original dash format
        client_paths = {
            "data_cicd_workflows": "data-cicd-workflows",
            "data_replication": "data-replication", 
            "data_orchestration": "data-orchestration",
            "bi": "bi",
            "data_catalog": "data-catalog",
            "data_quality": "data-quality",
            "data_governance": "data-governance",
            "data_modeling": "data-modeling",
            "platform_monitoring": "platform-monitoring",
            "platform_object_storage": "platform-object-storage",
            "user_console": "user-console"
        }
        
        # Template variable mappings - for cases where template uses different variable names
        template_var_mappings = {
            "data_cicd_workflows": "argo_workflows"  # Map data_cicd_workflows to argo_workflows
        }
        
        for client_name, domain_prefix, redirect_path, signout_path in clients:
            try:
                # Get the path name (with dashes) for vault lookup
                path_name = client_paths.get(client_name, client_name)
                
                # Get client ID and secret
                client_id = self.get_secret_from_vault(
                    secret_name="ClientID",
                    secret_path=f"/idp-sso/sso-clients-secrets/{path_name}/",
                    access_token=access_token
                )
                client_secret = self.get_secret_from_vault(
                    secret_name="ClientSecret",
                    secret_path=f"/idp-sso/sso-clients-secrets/{path_name}/",
                    access_token=access_token
                )
                
                # # Log the values being retrieved
                # logger.info(f"Processing client: {client_name}")
                # logger.info(f"Client ID retrieved: {client_id[:5] if client_id else 'None'}...")
                # logger.info(f"Client Secret retrieved: {client_secret[:5] if client_secret else 'None'}...")
                
                # Get template variable name (may be different from client_name)
                template_var_name = template_var_mappings.get(client_name, client_name)
                
                # Add client ID and secret to configs with template variable names
                client_configs[f"{template_var_name}_client_id"] = client_id
                client_configs[f"{template_var_name}_client_secret"] = client_secret
                
                # # Log what we're adding to client_configs
                # logger.info(f"Adding to client_configs with key: {template_var_name}_client_id")
                
                # Add redirect URL if domain prefix exists
                if domain_prefix:
                    redirect_url = f"https://{domain_prefix}.{self.customer_root_domain}{redirect_path}"
                    client_configs[f"{template_var_name}_redirect_url"] = redirect_url
                    # logger.info(f"Added redirect URL for {template_var_name}: {redirect_url}")
                    
                    if signout_path:
                        signout_url = f"https://{domain_prefix}.{self.customer_root_domain}{signout_path}"
                        client_configs[f"{template_var_name}_signout_redirect_url"] = signout_url
                        # logger.info(f"Added signout URL for {template_var_name}: {signout_url}")
                elif client_name == "user_console":
                    redirect_url = f"https://{self.customer_root_domain}{redirect_path}"
                    client_configs[f"{template_var_name}_redirect_url"] = redirect_url
                    client_configs[f"{template_var_name}_root_url"] = f"https://{self.customer_root_domain}"
                    # logger.info(f"Added URLs for {template_var_name}: {redirect_url}")
                    
            except Exception as e:
                logger.error(f"Error processing client {client_name}: {str(e)}")
                raise
        
        # Log final configs
        logger.info("Final client configs:")
        for key in client_configs.keys():
            logger.info(f"Key present: {key}")
        
        return client_configs

    @classmethod
    def from_cli_args(cls, args):
        """Create an IdpSsoManager instance from CLI arguments"""
        logger.info("Creating IdpSsoManager instance from CLI arguments")
        return cls(
            chart_version=args.chart_version,
            customer=args.customer,
            metadata_collector=args.metadata_collector,
            method=args.method,
            external_infisical_host=args.external_infisical_host,
            slug=args.project_slug,
            secret_manager_project_id=args.secret_manager_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            project_id=args.project_id,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            namespace=args.namespace,
            cloud_provider=args.cloud_provider,
            domain_name=args.domain_name
        )

if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "idp_sso_manager_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting IDP SSO Manager deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="IDP SSO Manager Deployment Tool",
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
        help='External Infisical host URL (required for external_infisical method)'
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
        help='Chart version for Keycloak'
    )
    required_args.add_argument(
        '--domain_name',
        required=True,
        help='Domain name for the customer'
    )
    required_args.add_argument(
        '--cloud_provider',
        required=True,
        choices=['gcp', 'aws', 'azure', 'self-managed'],
        help='Cloud provider where the cluster is running'
    )

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--project_slug',
        help='Project slug for the vault (required for local_vault method)'
    )
    optional_args.add_argument(
        '--secret_manager_project_id',
        help='Vault project ID (required for external_infisical method)'
    )
    optional_args.add_argument(
        '--client_id',
        help='Secret manager client ID (required for external_infisical method)'
    )
    optional_args.add_argument(
        '--client_secret',
        help='Secret manager client secret (required for external_infisical method)'
    )
    optional_args.add_argument(
        '--project_id',
        help='Cloud provider project ID (default: fast-bi-{customer} for GCP)'
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
        default='sso-keycloak',
        help='Kubernetes namespace for deployment (default: sso-keycloak)'
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

    # Parse arguments
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Deploying IDP SSO Manager for customer: {args.customer}")
        logger.info(f"Using vault method: {args.method}")
        logger.info(f"Cloud provider: {args.cloud_provider}")
        logger.info(f"Domain name: {args.domain_name}")
        
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

        # Create manager instance using the CLI factory method
        logger.info("Creating IdpSsoManager instance")
        manager = IdpSsoManager.from_cli_args(args)
        
        # Run the deployment
        logger.info("Starting deployment process")
        result = manager.run()
        
        logger.info("Execution Result: " + str(result))
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
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("IDP SSO Manager deployment script completed")
