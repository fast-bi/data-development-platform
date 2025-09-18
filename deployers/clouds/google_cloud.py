import subprocess
import os
import shutil
import json
import sys
import argparse
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import logging

# Handle imports for different execution contexts
try:
    from app.config import Config
    from flask import current_app
    FLASK_AVAILABLE = True
except ImportError:
    # Fallback for CLI usage when app module is not available
    class Config:
        CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
        CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    class current_app:
        @staticmethod
        def logger():
            return logging.getLogger(__name__)
    
    FLASK_AVAILABLE = False

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import time
import datetime

# Configure logging - only set up once
def setup_logging(log_file="gcp_deployment.log", debug=False):
    """Setup logging configuration to avoid duplication"""
    # Clear any existing handlers to prevent duplication
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configure root logger
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger('gcp_deployer')

# Initialize logger
logger = setup_logging()

class GoogleCloudManager:
    def __init__(self, deployment, billing_account_id, parent_folder, customer, domain_name, admin_email, whitelisted_ips, region, project_id=None, cloud_provider=None, 
                 cidr_block=None, cluster_ipv4_cidr_block=None, services_ipv4_cidr_block=None, private_service_connect_cidr=None,
                 lb_subnet_cidr=None, shared_host=None, kubernetes_version=None, gke_machine_type=None, gke_spot=None, k8s_master_ipv4_cidr_block=None,
                 terraform_state=None, state_project=None, state_location=None, state_bucket=None, gke_deployment_type=None,
                 service_account_key=None, access_token=None, refresh_token=None, token_expiry=None, token_key=None, metadata_collector=None):
        # Add these new attributes
        self.service_account_key = service_account_key
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.token_key = token_key
        self.metadata_collector = metadata_collector
        #Service specific tf - Basic
        self.cloud_provider = cloud_provider if cloud_provider else "gcp"
        self.deployment_environemnt = deployment
        self.billing_account_id = billing_account_id
        self.parent_folder = parent_folder
        self.customer = customer
        self.domain_name = domain_name
        self.region = region
        self.project_id = project_id if project_id else f"fast-bi-{customer}"
        self.admin_email = admin_email
        self.whitelisted_environment_ips = [whitelisted_ips] if isinstance(whitelisted_ips, str) else whitelisted_ips
        #Service specific tf - Advanced
        self.cidr_block = cidr_block
        self.cluster_ipv4_cidr_block = cluster_ipv4_cidr_block
        self.services_ipv4_cidr_block = services_ipv4_cidr_block
        self.private_service_connect_cidr = private_service_connect_cidr
        self.lb_subnet_cidr = lb_subnet_cidr
        self.shared_host = shared_host
        self.kubernetes_version = kubernetes_version
        self.gke_machine_type = gke_machine_type
        self.gke_spot = gke_spot
        self.k8s_master_ipv4_cidr_block = k8s_master_ipv4_cidr_block
        # New state management and GKE deployment type parameters
        self.terraform_state = terraform_state if terraform_state else "local"
        self.state_project = state_project
        self.state_location = state_location
        self.state_bucket = state_bucket
        self.gke_deployment_type = gke_deployment_type if gke_deployment_type else "zonal"
        #Service specific
        self.terragrunt_dir = os.path.abspath("terraform/google_cloud/terragrunt")
        self.backend_tf_template_path = f"terraform/google_cloud/templates/backend.tf_template"
        self.backend_tf_path = f"terraform/google_cloud/terragrunt/bi-platform/backend.tf"
        self.default_yaml_template_path = f"terraform/google_cloud/templates/defaults.yaml_template"
        self.default_yaml_path = f"terraform/google_cloud/terragrunt/defaults.yaml"
        self.env_yaml_template_path = f"terraform/google_cloud/templates/env.yaml_template"
        self.env_yaml_path = f"terraform/google_cloud/terragrunt/bi-platform/env.yaml"
        if self.deployment_environemnt == "basic":
            self.terragrunt_hcl_template_path = f"terraform/google_cloud/templates/terragrunt.hcl_basic_template"
        elif self.deployment_environemnt == "advanced":
            self.terragrunt_hcl_template_path = f"terraform/google_cloud/templates/terragrunt.hcl_advanced_template"
        else:
            raise Exception("Deployment environment is not supported")
        self.terragrunt_hcl_path  = f"terraform/google_cloud/terragrunt/bi-platform/terragrunt.hcl"
        #MetadataCollection

    def render_template(self, template_path, output_path, context):
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))
        output = template.render(context)
        with open(output_path, 'w') as f:
            f.write(output)
    
    def render_backend_tf(self):
        context = {
            'customer': self.customer,
            'state_bucket': self.state_bucket
        }
        self.render_template(self.backend_tf_template_path, self.backend_tf_path, context)
    
    def render_defaults_yaml(self):
        context = {
            'customer': self.customer,
            'project_id': self.project_id,
            'region': self.region
        }
        self.render_template(self.default_yaml_template_path, self.default_yaml_path, context)
    
    def render_env_yaml(self):
        context = {
            'project_id': self.project_id
        }
        self.render_template(self.env_yaml_template_path, self.env_yaml_path, context)
    
    def render_terragrunt_hcl(self):
        # Get GitLab access token from environment variables
        gitlab_access_token = os.environ.get('PUBLIC_ACCESS_TOKEN', '')
        if not gitlab_access_token:
            logger.warning("PUBLIC_ACCESS_TOKEN environment variable not set. GitLab module downloads may fail.")
        
        context = {
            'customer': self.customer,
            'domain_name': self.domain_name,
            'billing_account_id': self.billing_account_id,
            'region': self.region,
            'parent_folder': self.parent_folder,
            'project_id': self.project_id,
            'admin_email': self.admin_email,
            'whitelisted_ips': self.whitelisted_environment_ips,
            'cidr_block': self.cidr_block,
            'cluster_ipv4_cidr_block': self.cluster_ipv4_cidr_block,
            'services_ipv4_cidr_block': self.services_ipv4_cidr_block,
            'private_service_connect_cidr': self.private_service_connect_cidr,
            'lb_subnet_cidr': self.lb_subnet_cidr,
            'shared_host': self.shared_host,
            'kubernetes_version': self.kubernetes_version,
            'gke_machine_type': self.gke_machine_type,
            'gke_spot': self.gke_spot,
            'k8s_master_ipv4_cidr_block': self.k8s_master_ipv4_cidr_block,
            'terraform_state': self.terraform_state,
            'state_project': self.state_project,
            'state_location': self.state_location,
            'state_bucket': self.state_bucket,
            'gke_deployment_type': self.gke_deployment_type,
            'gitlab_access_token': gitlab_access_token
        }
        self.render_template(self.terragrunt_hcl_template_path, self.terragrunt_hcl_path, context)

    def refresh_access_token_if_needed(self):
        """Handle token refresh for API/website usage when tokens are provided"""
        if self.access_token and self.refresh_token:
            if self.is_token_expired():
                logger.info("Token is expired, attempting to refresh")
                try:
                    creds = Credentials.from_authorized_user_info(
                        {"refresh_token": self.refresh_token, "client_id": Config.CLIENT_ID, "client_secret": Config.CLIENT_SECRET},
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                    self.access_token = creds.token
                    
                    # Calculate new expiry
                    if creds.expiry:
                        self.token_expiry = creds.expiry.timestamp()
                    else:
                        # If expiry is not set, default to 1 hour from now
                        self.token_expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).timestamp()
                    
                    logger.info(f"New token expiry set to: {self.token_expiry}")
                    
                    # Update the token in the database if metadata_collector is available
                    if self.metadata_collector and hasattr(self.metadata_collector, 'save_token'):
                        self.metadata_collector.save_token(self.token_key, self.access_token, self.refresh_token, self.token_expiry)
                        logger.info("Token updated in database")
                except Exception as e:
                    logger.error(f"Error refreshing token: {str(e)}")
            else:
                logger.info("Token is still valid, no refresh needed")
        else:
            logger.info("No access token or refresh token provided, will use local gcloud authentication")

    def is_token_expired(self):
        if self.token_expiry is None:
            logger.info("Token expiry is None, considering as expired")
            return True
        current_time = time.time()
        is_expired = self.token_expiry <= current_time + 300
        logger.info(f"Token expiry: {datetime.datetime.fromtimestamp(self.token_expiry)}, "
                    f"Current time: {datetime.datetime.fromtimestamp(current_time)}, "
                    f"Is expired: {is_expired}")
        return is_expired

    def execute_command(self, command):
        self.refresh_access_token_if_needed()
        output_file_path = f"{self.customer}_deployment.log"
        original_dir = os.getcwd()  # Save the current directory
        try:
            # Change to the Terragrunt directory
            os.chdir(self.terragrunt_dir)
            logger.info("Changed directory to: %s", os.getcwd())
            logger.info("Executing command: %s", ' '.join(command))

            env = os.environ.copy()
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                env['GOOGLE_APPLICATION_CREDENTIALS'] = os.environ['GOOGLE_APPLICATION_CREDENTIALS']

            result = subprocess.run(command, env=env, check=True, capture_output=True, text=True, shell=True)
            
            # Save the result to a file
            with open(output_file_path, 'w') as f:
                f.write(result.stdout)
                f.write(result.stderr)
            
            return result.stdout + result.stderr, None
        except subprocess.CalledProcessError as e:
            logger.error("Command failed: %s", e.cmd)
            logger.error("Status code: %s", e.returncode)
            logger.error("Output: %s", e.stdout)
            logger.error("Error: %s", e.stderr)
            return e.stdout + e.stderr, e
        finally:
            # Change back to the original directory
            os.chdir(original_dir)
            logger.info("Returned to original directory: %s", os.getcwd())


    def cleanup_terraform_states(self):
        # Path where terragrunt and terraform files are located
        base_dir = self.terragrunt_dir

        # Walk through all directories and files in the base directory
        for root, dirs, files in os.walk(base_dir, topdown=False):
            # Remove .terragrunt-cache directories
            for name in dirs:
                if name == ".terragrunt-cache":
                    full_path = os.path.join(root, name)
                    shutil.rmtree(full_path)
                    logger.info(f"Removed .terragrunt-cache: {full_path}")
                elif name == ".terraform":
                    # For .terraform directories, check if they contain state files
                    terraform_dir = os.path.join(root, name)
                    customer_state_dir = os.path.join(terraform_dir, self.customer)
                    
                    # If this .terraform directory contains customer state files, preserve it
                    if os.path.exists(customer_state_dir):
                        logger.info(f"Preserving .terraform directory with state files: {terraform_dir}")
                        continue
                    else:
                        # This .terraform directory doesn't contain our customer's state files, safe to remove
                        shutil.rmtree(terraform_dir)
                        logger.info(f"Removed .terraform directory without state files: {terraform_dir}")

            # Remove .terraform.lock.hcl files (these are safe to remove and will be regenerated)
            for name in files:
                if name == ".terraform.lock.hcl":
                    full_path = os.path.join(root, name)
                    os.remove(full_path)
                    logger.info(f"Removed .terraform.lock.hcl: {full_path}")
        
        logger.info("Cleanup completed successfully.")

    def check_gcloud_auth(self):
        """Check if gcloud authentication is properly configured"""
        try:
            result = subprocess.run("gcloud auth list --filter=status:ACTIVE --format=value(account)", 
                                  capture_output=True, text=True, check=True, shell=True)
            if result.stdout.strip():
                logger.info(f"gcloud authentication found for account: {result.stdout.strip()}")
                return True
            else:
                logger.warning("No active gcloud authentication found")
                return False
        except subprocess.CalledProcessError:
            logger.error("gcloud command failed")
            return False
        except FileNotFoundError:
            logger.error("gcloud CLI not found")
            return False

    def deploy_gcp_terragrunt(self, max_retries=3):
        self.refresh_access_token_if_needed()
        retry_count = 0
        while True:
            try:
                self.cleanup_terraform_states()
                
                # Handle different authentication methods
                if self.access_token and self.refresh_token:
                    logger.info("Using OAuth2 access token for authentication (API/Website mode)")
                    # Create a temporary credentials file for OAuth2 tokens
                    creds_file = os.path.join(self.terragrunt_dir, 'temp_creds.json')
                    with open(creds_file, 'w') as f:
                        json.dump({
                            "type": "authorized_user",
                            "client_id": Config.CLIENT_ID,
                            "client_secret": Config.CLIENT_SECRET,
                            "refresh_token": self.refresh_token,
                            "access_token": self.access_token
                        }, f)
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_file
                elif self.service_account_key:
                    logger.info("Using service account key for authentication")
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.service_account_key
                else:
                    logger.info("Using local gcloud authentication (CLI mode)")
                    # Check if user is authenticated with gcloud
                    try:
                        result = subprocess.run("gcloud auth list --filter=status:ACTIVE --format=value(account)", 
                                              capture_output=True, text=True, check=True, shell=True)
                        if result.stdout.strip():
                            logger.info(f"Using gcloud authentication for account: {result.stdout.strip()}")
                        else:
                            raise Exception("No active gcloud authentication found. Please run 'gcloud auth login' first.")
                    except subprocess.CalledProcessError:
                        raise Exception("gcloud command failed. Please ensure gcloud CLI is installed and run 'gcloud auth login' first.")
                    except FileNotFoundError:
                        raise Exception("gcloud CLI not found. Please install Google Cloud SDK and run 'gcloud auth login' first.")

                # Run Terragrunt
                output_message, exc = self.execute_command([
                    "terragrunt", "apply", "--all",
                    "--parallelism=1",
                    "--non-interactive",
                    "--no-color",
                    "--log-format=json",
                    "--log-level=error"
                ])
                if exc:
                    raise exc
                return {
                    "output": output_message,
                    "status": "success"
                }
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    return {
                        "output": str(e),
                        "status": "failure"
                    }
                logger.warning("Retry %s/%s after error: %s", retry_count, max_retries, e)
                time.sleep(5)  # wait for 5 seconds before retrying
            finally:
                self.cleanup_terraform_states()
                # Remove the temporary credentials file if it was created
                if os.path.exists(os.path.join(self.terragrunt_dir, 'temp_creds.json')):
                    os.remove(os.path.join(self.terragrunt_dir, 'temp_creds.json'))

    def run(self):
        """Main execution method"""
        logger.info("Starting GCP infrastructure deployment for customer: %s", self.customer)
        try:
            # Render all template files
            logger.info("Rendering Terraform template files")
            if self.terraform_state == "remote":
                self.render_backend_tf()
            self.render_defaults_yaml()
            self.render_env_yaml()
            self.render_terragrunt_hcl()
            
            # Deploy infrastructure
            logger.info("Deploying GCP infrastructure using Terragrunt")
            result = self.deploy_gcp_terragrunt()
            
            if result["status"] == "success":
                logger.info("GCP infrastructure deployment completed successfully")
                
                # Add deployment record to metadata collector if available
                if self.metadata_collector:
                    deployment_record = {
                        "customer": self.customer,
                        "deployment_environment": self.deployment_environemnt,
                        "cloud_provider": self.cloud_provider,
                        "project_id": self.project_id,
                        "region": self.region,
                        "deploy_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "status": "success"
                    }
                    self.metadata_collector.add_deployment_record(deployment_record)
                    logger.info("Deployment record added to metadata collector")
                
                return "GCP infrastructure deployed successfully"
            else:
                logger.error("GCP infrastructure deployment failed")
                return f"GCP infrastructure deployment failed: {result['output']}"
                
        except Exception as e:
            logger.error("Deployment failed: %s", str(e))
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a GoogleCloudManager instance from CLI arguments"""
        logger.info("Creating GoogleCloudManager instance from CLI arguments")
        return cls(
            deployment=args.deployment,
            billing_account_id=args.billing_account_id,
            parent_folder=args.parent_folder,
            customer=args.customer,
            domain_name=args.domain_name,
            admin_email=args.admin_email,
            whitelisted_ips=args.whitelisted_ips,
            region=args.region,
            project_id=args.project_id,
            cloud_provider=args.cloud_provider,
            cidr_block=args.cidr_block,
            cluster_ipv4_cidr_block=args.cluster_ipv4_cidr_block,
            services_ipv4_cidr_block=args.services_ipv4_cidr_block,
            private_service_connect_cidr=args.private_service_connect_cidr,
            lb_subnet_cidr=args.lb_subnet_cidr,
            shared_host=args.shared_host,
            kubernetes_version=args.kubernetes_version,
            gke_machine_type=args.gke_machine_type,
            gke_spot=args.gke_spot,
            k8s_master_ipv4_cidr_block=args.k8s_master_ipv4_cidr_block,
            terraform_state=args.terraform_state,
            state_project=args.state_project,
            state_location=args.state_location,
            state_bucket=args.state_bucket,
            gke_deployment_type=args.gke_deployment_type,
            service_account_key=args.service_account_key,
            access_token=args.access_token,
            refresh_token=args.refresh_token,
            token_expiry=args.token_expiry,
            token_key=args.token_key,
            metadata_collector=args.metadata_collector
        )


if __name__ == "__main__":
    # Parse arguments first to check for debug flag
    parser = argparse.ArgumentParser(
        description="GCP Infrastructure Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add debug argument early so we can use it for logging setup
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    # Parse only the debug argument for now
    args, _ = parser.parse_known_args()
    
    # Setup logging with debug flag if provided
    logger = setup_logging(debug=args.debug)
    logger.info("Starting GCP deployment script")

    # Required core arguments
    required_args = parser.add_argument_group('required core arguments')
    required_args.add_argument(
        '--deployment',
        required=True,
        choices=['basic', 'advanced'],
        help='Deployment environment (basic or advanced)'
    )
    required_args.add_argument(
        '--billing_account_id',
        required=True,
        help='GCP billing account ID'
    )
    required_args.add_argument(
        '--parent_folder',
        required=True,
        help='GCP parent folder ID'
    )
    required_args.add_argument(
        '--customer',
        required=True,
        help='Customer tenant name (lowercase letters, numbers, and hyphens only)'
    )
    required_args.add_argument(
        '--domain_name',
        required=True,
        help='Domain name for the customer (e.g., fast.bi)'
    )
    required_args.add_argument(
        '--admin_email',
        required=True,
        help='Admin email address'
    )
    required_args.add_argument(
        '--whitelisted_ips',
        required=True,
        help='Comma-separated list of whitelisted IP addresses'
    )
    required_args.add_argument(
        '--region',
        required=True,
        help='GCP region for deployment'
    )

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--project_id',
        help='GCP project ID (default: fast-bi-{customer})'
    )
    optional_args.add_argument(
        '--cloud_provider',
        default='gcp',
        help='Cloud provider (default: gcp)'
    )
    optional_args.add_argument(
        '--cidr_block',
        help='CIDR block for VPC'
    )
    optional_args.add_argument(
        '--cluster_ipv4_cidr_block',
        help='Cluster IPv4 CIDR block'
    )
    optional_args.add_argument(
        '--services_ipv4_cidr_block',
        help='Services IPv4 CIDR block'
    )
    optional_args.add_argument(
        '--private_service_connect_cidr',
        help='Private service connect CIDR'
    )
    optional_args.add_argument(
        '--lb_subnet_cidr',
        help='Load balancer subnet CIDR'
    )
    optional_args.add_argument(
        '--shared_host',
        help='Shared host configuration'
    )
    optional_args.add_argument(
        '--kubernetes_version',
        help='Kubernetes version'
    )
    optional_args.add_argument(
        '--gke_machine_type',
        help='GKE machine type'
    )
    optional_args.add_argument(
        '--gke_spot',
        help='GKE spot instance configuration'
    )
    optional_args.add_argument(
        '--k8s_master_ipv4_cidr_block',
        help='Kubernetes master IPv4 CIDR block'
    )
    optional_args.add_argument(
        '--terraform_state',
        choices=['local', 'remote'],
        default='local',
        help='Terraform state backend type (default: local)'
    )
    optional_args.add_argument(
        '--state_project',
        help='GCP project ID for remote state bucket (required if terraform_state=remote)'
    )
    optional_args.add_argument(
        '--state_location',
        help='GCS bucket location for remote state (required if terraform_state=remote)'
    )
    optional_args.add_argument(
        '--state_bucket',
        help='GCS bucket name for remote state (required if terraform_state=remote)'
    )
    optional_args.add_argument(
        '--gke_deployment_type',
        choices=['zonal', 'multizone'],
        default='zonal',
        help='GKE deployment type: zonal for free tier, multizone for production (default: zonal)'
    )

    # Authentication arguments
    auth_args = parser.add_argument_group('authentication')
    auth_args.add_argument(
        '--service_account_key',
        help='Path to service account key file (for service account authentication)'
    )
    auth_args.add_argument(
        '--access_token',
        help='OAuth2 access token (for API/website authentication - use with refresh_token)'
    )
    auth_args.add_argument(
        '--refresh_token',
        help='OAuth2 refresh token (for API/website authentication - use with access_token)'
    )
    auth_args.add_argument(
        '--token_expiry',
        type=float,
        help='Token expiry timestamp (for API/website authentication)'
    )
    auth_args.add_argument(
        '--token_key',
        help='Token key for database storage (for API/website authentication)'
    )
    auth_args.add_argument(
        '--use_gcloud_auth',
        action='store_true',
        help='Use local gcloud authentication (run "gcloud auth login" first)'
    )

    # Metadata arguments
    metadata_args = parser.add_argument_group('metadata')
    metadata_args.add_argument(
        '--metadata_file',
        default='deployment_metadata.json',
        help='Path to metadata file (default: deployment_metadata.json)'
    )
    metadata_args.add_argument(
        '--skip_metadata',
        action='store_true',
        help='Skip metadata collection (for CLI usage)'
    )
    # Parse arguments
    args = parser.parse_args()

    try:
        logger.info("Deploying GCP infrastructure for customer: %s", args.customer)
        logger.info("Deployment environment: %s", args.deployment)
        
        # Check authentication method
        auth_methods = []
        if args.service_account_key:
            auth_methods.append("service account key")
        if args.access_token and args.refresh_token:
            auth_methods.append("OAuth2 tokens")
        if args.use_gcloud_auth or (not args.service_account_key and not args.access_token):
            auth_methods.append("gcloud CLI")
        
        if len(auth_methods) > 1:
            logger.warning("Multiple authentication methods specified: %s. Using priority order.", ", ".join(auth_methods))
        
        # If using gcloud auth, check if it's properly configured
        if args.use_gcloud_auth or (not args.service_account_key and not args.access_token):
            logger.info("Checking gcloud authentication...")
            # Note: We'll check this again in the deployment method, but provide early feedback
            logger.info("Make sure you have run 'gcloud auth login' and 'gcloud config set project %s'", 
                       args.project_id if args.project_id else f"fast-bi-{args.customer}")
        
        # Create a simple metadata collector for CLI usage
        class SimpleMetadataCollector:
            def __init__(self, metadata_file):
                self.metadata_file = metadata_file
                self.deployment_records = []
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r') as f:
                            self.deployment_records = json.load(f)
                            logger.info("Loaded %s existing deployment records", len(self.deployment_records))
                    except json.JSONDecodeError:
                        logger.warning("Could not parse %s, starting with empty records", metadata_file)
                        self.deployment_records = []
                else:
                    logger.info("Metadata file %s not found, will create new file", metadata_file)
            
            def add_deployment_record(self, record):
                self.deployment_records.append(record)
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(os.path.abspath(self.metadata_file)), exist_ok=True)
                    with open(self.metadata_file, 'w') as f:
                        json.dump(self.deployment_records, f, indent=2)
                    logger.info("Deployment record added to %s", self.metadata_file)
                except Exception as e:
                    logger.error("Failed to write metadata to %s: %s", self.metadata_file, str(e))

        # Use the appropriate metadata collector
        if args.skip_metadata:
            logger.info("Metadata collection is disabled")
            class DummyMetadataCollector:
                def add_deployment_record(self, record):
                    logger.info("Metadata collection skipped")
            metadata_collector = DummyMetadataCollector()
        else:
            logger.info("Using metadata file: %s", args.metadata_file)
            metadata_collector = SimpleMetadataCollector(args.metadata_file)

        # Add metadata collector to args for from_cli_args method
        args.metadata_collector = metadata_collector

        # Create deployer instance using the CLI factory method
        logger.info("Creating GoogleCloudManager instance")
        deployer = GoogleCloudManager.from_cli_args(args)
        
        # Run the deployment
        logger.info("Starting deployment process")
        result = deployer.run()
        
        logger.info("Execution Result: %s", str(result))
        print("Execution Result:")
        print(result)
        
    except FileNotFoundError as e:
        logger.error("File not found error: %s", str(e))
        print(f"File not found error: {str(e)}")
        sys.exit(1)
    except ValueError as e:
        logger.error("Invalid value error: %s", str(e))
        print(f"Invalid value error: {str(e)}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error("Command execution failed: %s", str(e))
        print(f"Command execution failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", str(e), exc_info=True)
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("GCP deployment script completed")