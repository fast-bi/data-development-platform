import os
import sys
import json
import yaml
import click
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import questionary
from questionary import Style


# Set required environment variables for CLI usage
import os
os.environ.setdefault('SECRET_KEY', 'cli-secret-key-for-deployment')
os.environ.setdefault('MAIL_SERVER', 'mail.smtp2go.com')
os.environ.setdefault('MAIL_PORT', '2525')
os.environ.setdefault('MAIL_USERNAME', 'cli-user')
os.environ.setdefault('MAIL_PASSWORD', 'cli-password')
os.environ.setdefault('MAIL_DEFAULT_SENDER', 'no-reply@fast.bi')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_USER', 'cli-user')
os.environ.setdefault('DB_PASSWORD', 'cli-password')
os.environ.setdefault('DB_NAME', 'cli-db')
os.environ.setdefault('GOOGLE_CLIENT_ID', 'cli-client-id')
os.environ.setdefault('GOOGLE_CLIENT_SECRET', 'cli-client-secret')
os.environ.setdefault('GOOGLE_REDIRECT_URI', 'http://localhost:8080/callback')
os.environ.setdefault('GITLAB_ADMIN_ACCESS_TOKEN', 'cli-token')

# Import the Deployer class'es directly
from deployers.clouds.google_cloud import GoogleCloudManager
from utils.customer_secret_manager_operations import CustomerSecretManager

# Configure questionary to allow pasting
questionary.Style.from_dict({
    'qmark': 'fg:yellow bold',
    'question': 'bold',
    'answer': 'fg:green bold',
    'input': 'fg:cyan',
    'pointer': 'fg:yellow bold',
    'highlighted': 'fg:blue bold',
    'selected': 'fg:cyan',
    'separator': '',
    'instruction': '',
    'text': '',
    'disabled': 'fg:gray italic'
})

def safe_input(prompt: str, default: str = "", validate=None) -> str:
    """Helper function for input with better paste support"""
    while True:
        try:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if validate:
                try:
                    validate(user_input)
                except Exception as e:
                    click.echo(f"❌ Validation error: {str(e)}")
                    continue
            
            return user_input
        except KeyboardInterrupt:
            click.echo("\n❌ Input cancelled")
            raise click.Abort()
        except EOFError:
            click.echo("\n❌ Input cancelled")
            raise click.Abort()

def safe_select(prompt: str, choices: list) -> str:
    """Helper function for selection with better paste support"""
    click.echo(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        click.echo(f"{i}. {choice}")
    
    while True:
        try:
            choice = input(f"Enter choice (1-{len(choices)}): ").strip()
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
            click.echo(f"❌ Please enter a number between 1 and {len(choices)}")
        except KeyboardInterrupt:
            click.echo("\n❌ Input cancelled")
            raise click.Abort()
        except EOFError:
            click.echo("\n❌ Input cancelled")
            raise click.Abort()

def safe_input_long_credential(prompt: str, default: str = "") -> str:
    """Special function for handling long credentials like base64 strings"""
    click.echo(f"\n{prompt}")
    click.echo("💡 Tip: You can paste long credentials. If pasting fails, try:")
    click.echo("   1. Right-click and select 'Paste'")
    click.echo("   2. Use Cmd+V (Mac) or Ctrl+V (Windows/Linux)")
    click.echo("   3. Or type 'file:' followed by path to a file containing the credential")
    
    while True:
        try:
            if default:
                user_input = input(f"Enter credential [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input("Enter credential: ").strip()
            
            # Check if user wants to read from file
            if user_input.startswith('file:'):
                file_path = user_input[5:].strip()
                try:
                    with open(file_path, 'r') as f:
                        user_input = f.read().strip()
                    click.echo(f"✅ Credential loaded from file: {file_path}")
                except Exception as e:
                    click.echo(f"❌ Error reading file {file_path}: {str(e)}")
                    continue
            
            if not user_input:
                click.echo("❌ Credential cannot be empty")
                continue
            
            return user_input
        except KeyboardInterrupt:
            click.echo("\n❌ Input cancelled")
            raise click.Abort()
        except EOFError:
            click.echo("\n❌ Input cancelled")
            raise click.Abort()

def validate_and_normalize_repo_url(repo_url: str, access_method: str) -> str:
    """Validate and normalize repository URL based on access method"""
    if not repo_url or not repo_url.strip():
        raise ValueError("Repository URL cannot be empty")
    
    # Remove any trailing whitespace
    repo_url = repo_url.strip()
    
    # Check if URL is valid format
    if not (repo_url.startswith('https://') or repo_url.startswith('git@')):
        raise ValueError(f"Invalid repository URL format: {repo_url}. Must start with 'https://' or 'git@'")
    
    # For deploy keys, ensure SSH format
    if access_method == 'deploy_keys':
        if repo_url.startswith('https://'):
            # Convert https://github.com/owner/repo.git to git@github.com:owner/repo.git
            url_without_protocol = repo_url.replace('https://', '')
            if '/' in url_without_protocol:
                domain, path = url_without_protocol.split('/', 1)
                return f"git@{domain}:{path}"
        return repo_url
    
    # For access token, ensure HTTPS format
    elif access_method == 'access_token':
        if repo_url.startswith('git@'):
            # Convert git@github.com:owner/repo.git to https://github.com/owner/repo.git
            at_split = repo_url.split('@', 1)
            host_and_path = at_split[1]
            host, sep, path = host_and_path.partition(':')
            return f"https://{host}/{path}"
        return repo_url
    
    return repo_url

class DeploymentState:
    """Class to manage deployment state across phases"""
    def __init__(self):
        self.config = {}
        self.kubeconfig_path = None
        self.infrastructure_deployed = False
        self.secrets_generated = False
        self.repositories_configured = False
        self.infra_services_deployed = False
        self.data_services_deployed = False
        self.deployment_finalized = False
        # Individual service deployment tracking
        self.deployed_services = {
            "infrastructure_services": {},
            "data_services": {}
        }

    def save_state(self, filename: str = "cli/state/deployment_state.json"):
        """Save current state to file"""
        # Ensure the state directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        state_data = {
            'config': self.config,
            'kubeconfig_path': self.kubeconfig_path,
            'infrastructure_deployed': self.infrastructure_deployed,
            'secrets_generated': self.secrets_generated,
            'repositories_configured': self.repositories_configured,
            'infra_services_deployed': self.infra_services_deployed,
            'data_services_deployed': self.data_services_deployed,
            'deployment_finalized': self.deployment_finalized,
            'deployed_services': self.deployed_services
        }
        with open(filename, 'w') as f:
            json.dump(state_data, f, indent=2)

    def load_state(self, filename: str = "cli/state/deployment_state.json"):
        """Load state from file"""
        if Path(filename).exists():
            with open(filename, 'r') as f:
                state_data = json.load(f)
                self.config = state_data.get('config', {})
                self.kubeconfig_path = state_data.get('kubeconfig_path')
                self.infrastructure_deployed = state_data.get('infrastructure_deployed', False)
                self.secrets_generated = state_data.get('secrets_generated', False)
                self.repositories_configured = state_data.get('repositories_configured', False)
                self.infra_services_deployed = state_data.get('infra_services_deployed', False)
                self.data_services_deployed = state_data.get('data_services_deployed', False)
                self.deployment_finalized = state_data.get('deployment_finalized', False)
                self.deployed_services = state_data.get('deployed_services', {
                    "infrastructure_services": {},
                    "data_services": {}
                })
    
    def mark_service_deployed(self, service_type: str, service_name: str, deployment_info: dict = None):
        """Mark a specific service as deployed"""
        if service_type not in self.deployed_services:
            self.deployed_services[service_type] = {}
        
        self.deployed_services[service_type][service_name] = {
            'deployed': True,
            'deployed_at': datetime.now().isoformat(),
            'deployment_info': deployment_info or {}
        }
    
    def is_service_deployed(self, service_type: str, service_name: str) -> bool:
        """Check if a specific service is deployed"""
        return self.deployed_services.get(service_type, {}).get(service_name, {}).get('deployed', False)

def load_config_from_file(config_file: str) -> Dict:
    """Load configuration from YAML file"""
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Transform the YAML structure to match our CLI state structure
        transformed_config = {}
        
        # Basic configuration
        if 'basic' in config_data:
            basic = config_data['basic']
            transformed_config.update({
                'customer': basic.get('customer', '').replace('*', ''),
                'user_email': basic.get('user_email', '').replace('*', ''),
                'cloud_provider': basic.get('cloud_provider', '').replace('*', ''),
                'project_region': basic.get('project_region', '').replace('*', ''),
                'domain_name': basic.get('domain_name', '').replace('*', '')
            })
        
        # Infrastructure configuration - handle different cloud providers
        if 'infrastructure_deployment' in config_data:
            infra = config_data['infrastructure_deployment']
            cloud_provider = transformed_config.get('cloud_provider', 'gcp')
            
            # Handle GCP configuration
            if 'gcp' in infra:
                gcp = infra['gcp']
                transformed_config.update({
                    'gcp_deployment_type': gcp.get('deployment_type', 'basic'),
                    'gcp_billing_account_id': gcp.get('billing_account_id', '').replace('*', ''),
                    'gcp_parent_folder': gcp.get('parent_folder', '').replace('*', ''),
                    'gcp_whitelisted_ips': gcp.get('whitelisted_ips', '') if isinstance(gcp.get('whitelisted_ips', ''), list) else gcp.get('whitelisted_ips', '').replace('*', ''),
                    'gcp_cidr_block': gcp.get('cidr_block', ''),
                    'gcp_cluster_ipv4_cidr_block': gcp.get('cluster_ipv4_cidr_block', ''),
                    'gcp_services_ipv4_cidr_block': gcp.get('services_ipv4_cidr_block', ''),
                    'gcp_private_service_connect_cidr': gcp.get('private_service_connect_cidr', ''),
                    'gcp_lb_subnet_cidr': gcp.get('lb_subnet_cidr', ''),
                    'gcp_kubernetes_version': gcp.get('kubernetes_version', ''),
                    'gcp_gke_machine_type': gcp.get('gke_machine_type', ''),
                    'gcp_gke_spot': gcp.get('gke_spot', ''),
                    'gcp_k8s_master_ipv4_cidr_block': gcp.get('k8s_master_ipv4_cidr_block', ''),
                    'gcp_shared_host': gcp.get('shared_host', ''),
                    'gcp_terraform_state': gcp.get('terraform_state'),
                    'gcp_state_project': gcp.get('state_project', '').replace('*', ''),
                    'gcp_state_location': gcp.get('state_location', '').replace('*', ''),
                    'gcp_state_bucket': gcp.get('state_bucket', '').replace('*', ''),
                    'gcp_gke_deployment_type': gcp.get('gke_deployment_type')
                })
            
            # Handle AWS configuration
            elif 'aws' in infra:
                aws = infra['aws']
                transformed_config.update({
                    'aws_access_key_id': aws.get('aws_access_key_id', '').replace('*', ''),
                    'aws_secret_access_key': aws.get('aws_secret_access_key', '').replace('*', ''),
                    'aws_region': aws.get('aws_region', '').replace('*', ''),
                    'aws_vpc_cidr': aws.get('vpc_cidr', ''),
                    'aws_cluster_name': aws.get('cluster_name', ''),
                    'aws_node_group_name': aws.get('node_group_name', ''),
                    'aws_instance_type': aws.get('instance_type', ''),
                    'aws_desired_capacity': aws.get('desired_capacity', ''),
                    'aws_max_capacity': aws.get('max_capacity', ''),
                    'aws_min_capacity': aws.get('min_capacity', '')
                })
            
            # Handle Azure configuration
            elif 'azure' in infra:
                azure = infra['azure']
                transformed_config.update({
                    'azure_subscription_id': azure.get('subscription_id', '').replace('*', ''),
                    'azure_tenant_id': azure.get('tenant_id', '').replace('*', ''),
                    'azure_client_id': azure.get('client_id', '').replace('*', ''),
                    'azure_client_secret': azure.get('client_secret', '').replace('*', ''),
                    'azure_resource_group': azure.get('resource_group', '').replace('*', ''),
                    'azure_location': azure.get('location', '').replace('*', ''),
                    'azure_vnet_cidr': azure.get('vnet_cidr', ''),
                    'azure_subnet_cidr': azure.get('subnet_cidr', ''),
                    'azure_vm_size': azure.get('vm_size', '')
                })
            
            # Handle On-Premises configuration
            elif 'onprem' in infra:
                onprem = infra['onprem']
                transformed_config.update({
                    'onprem_kubeconfig_path': onprem.get('kubeconfig_path', '').replace('*', ''),
                    'onprem_cluster_name': onprem.get('cluster_name', '').replace('*', ''),
                    'onprem_storage_class': onprem.get('storage_class', '').replace('*', '')
                })
        
        # Secrets configuration
        if 'secrets' in config_data:
            secrets = config_data['secrets']
            transformed_config.update({
                'secrets_vault_method': secrets.get('vault_method', '').replace('*', ''),
                'secrets_data_analysis_platform': secrets.get('data_analysis_platform', '').replace('*', ''),
                'secrets_data_warehouse_platform': secrets.get('data_warehouse_platform', '').replace('*', ''),
                'secrets_orchestrator_platform': secrets.get('orchestrator_platform', '').replace('*', ''),
                'secrets_git_provider': secrets.get('git_provider', '').replace('*', ''),
                'secrets_dag_repo_url': secrets.get('dag_repo_url', '').replace('*', ''),
                'secrets_data_repo_url': secrets.get('data_repo_url', '').replace('*', ''),
                'secrets_data_repo_main_branch': secrets.get('data_repo_main_branch', '').replace('*', ''),
                'secrets_repo_access_method': secrets.get('repo_access_method', '').replace('*', ''),
                'secrets_git_provider_access_token': secrets.get('git_provider_access_token', ''),
                'secrets_smtp_host': secrets.get('smtp_host', ''),
                'secrets_smtp_port': secrets.get('smtp_port', ''),
                'secrets_smtp_username': secrets.get('smtp_username', ''),
                'secrets_smtp_password': secrets.get('smtp_password', ''),
                # BigQuery specific parameters (optional in YAML, required when using BigQuery)
                'secrets_bigquery_project_id': secrets.get('bigquery_project_id', '').replace('*', ''),
                'secrets_bigquery_region': secrets.get('bigquery_region', '').replace('*', ''),
                # Cloud provider specific service account credentials (file paths)
                'secrets_data_platform_sa_file': secrets.get('data_platform_sa_file', '').replace('*', ''),
                'secrets_data_analysis_sa_file': secrets.get('data_analysis_sa_file', '').replace('*', '')
            })
        
        # Infrastructure services configuration
        if 'infrastructure_services' in config_data:
            infra = config_data['infrastructure_services']
            transformed_config.update({
                # external_ip will be auto-read from terraform output, but allow override
                'infra_external_ip': infra.get('external_ip', '').replace('*', '') if infra.get('external_ip') else '',
                'infra_whitelisted_ips': infra.get('whitelisted_environment_ips', '') if isinstance(infra.get('whitelisted_environment_ips', ''), list) else infra.get('whitelisted_environment_ips', '').replace('*', ''),
                'infra_external_dns_domain_filters': infra.get('external_dns_domain_filters', '').replace('*', '')
            })
        
        # Data services configuration
        if 'data_services' in config_data:
            data = config_data['data_services']
            transformed_config.update({
                'data_git_provider': data.get('git_provider', ''),
                'data_git_runner_token': data.get('git_runner_access_token', '').replace('*', ''),
                'data_replication_destination_type': data.get('data_replication_default_destination_type', ''),
                'data_bi_system': data.get('bi_system', ''),
                'data_governance_vault_secrets': data.get('vault_secrets', ''),
                'user_console_web_core_version': data.get('tsb_fastbi_web_core_image_version', '').replace('*', ''),
                'user_console_dbt_init_version': data.get('tsb_dbt_init_core_image_version', '').replace('*', '')
            })
        
        # Finalization configuration
        if 'finalization' in config_data:
            final = config_data['finalization']
            transformed_config.update({
                'finalization_git_provider': final.get('git_provider', ''),
                'finalization_git_access_token': final.get('git_access_token', ''),
                'finalization_git_repo_url': final.get('git_repo_url', '').replace('*', '')
            })
        
        # Deployment options
        if 'deployment' in config_data:
            deployment = config_data['deployment']
            transformed_config.update({
                'phases_to_run': deployment.get('phases_to_run', 'all'),
                'interactive': deployment.get('interactive', False),
                'skip_confirmations': deployment.get('skip_confirmations', True),
                'state_file': deployment.get('state_file', 'cli/state/deployment_state.json')
            })
        
        return transformed_config
        
    except Exception as e:
        click.echo(f"❌ Error loading configuration file: {str(e)}")
        raise click.Abort()

class DeploymentManager:
    """Main class to manage the entire deployment process"""
    def __init__(self, state: DeploymentState, config_file: str = None, non_interactive: bool = False):
        self.state = state
        self.secret_manager = None
        self.deployment_session_id = None
        self.realm_info = None
        self.config_file = config_file
        self.non_interactive = non_interactive
        
        # Load configuration from file if provided
        if config_file:
            config_data = load_config_from_file(config_file)
            self.state.config.update(config_data)
            self.state.save_state()

    def phase_1_infrastructure(self) -> bool:
        """Phase 1: Infrastructure Deployment"""
        click.echo("\n🚀 PHASE 1: Infrastructure Deployment")
        
        if self.state.infrastructure_deployed:
            click.echo("✅ Infrastructure already deployed")
            return True

        # In non-interactive mode, automatically choose new infrastructure deployment
        if self.non_interactive:
            infrastructure_choice = "Deploy new infrastructure"
            click.echo(f"🤖 Non-interactive mode: {infrastructure_choice}")
        else:
            # Ask user what type of infrastructure they want to use
            infrastructure_choice = safe_select(
                "Choose infrastructure deployment option:",
                [
                    "Deploy new infrastructure",
                    "Use existing infrastructure (provide kubeconfig)"
                ]
            )
        
        if infrastructure_choice == "Deploy new infrastructure":
            return self._deploy_new_infrastructure()
        else:
            return self._use_existing_infrastructure()

    def _deploy_new_infrastructure(self) -> bool:
        """Deploy new cloud infrastructure"""
        click.echo("🚀 Deploying new cloud infrastructure...")
        
        # Use the cloud provider from the state (already collected in basic config)
        cloud_provider = self.state.config['cloud_provider']
        click.echo(f"🔧 Using cloud provider: {cloud_provider}")
        
        if cloud_provider == 'gcp':
            return self._deploy_gcp_infrastructure()
        elif cloud_provider == 'aws':
            click.echo("❌ AWS deployment not implemented yet")
            return False
        elif cloud_provider == 'azure':
            click.echo("❌ Azure deployment not implemented yet")
            return False
        elif cloud_provider == 'onprem':
            return self._deploy_onprem_infrastructure()
        else:
            click.echo(f"❌ Unsupported cloud provider: {cloud_provider}")
            return False

    def _deploy_gcp_infrastructure(self) -> bool:
        """Deploy GCP infrastructure using the GoogleCloudManager class directly"""
        click.echo("🔧 Deploying GCP infrastructure...")
        
        # Collect GCP-specific parameters (only ask for what's not already in state)
        gcp_config = self._collect_gcp_parameters()
        
        # Show deployment configuration
        click.echo(f"\n📋 GCP Deployment Configuration:")
        click.echo(f"  Deployment Type: {gcp_config['deployment']}")
        click.echo(f"  Customer: {self.state.config['customer']}")
        click.echo(f"  Project ID: {gcp_config['project_id']}")
        click.echo(f"  Region: {self.state.config['project_region']}")
        click.echo(f"  Domain: {self.state.config['domain_name']}")
        click.echo(f"  Admin Email: {self.state.config['user_email']}")
        click.echo(f"  Billing Account ID: {gcp_config['billing_account_id']}")
        click.echo(f"  Parent Folder: {gcp_config['parent_folder']}")
        # Display whitelisted IPs properly (handle both lists and strings)
        if isinstance(gcp_config['whitelisted_ips'], list):
            click.echo(f"  Whitelisted IPs: {', '.join(gcp_config['whitelisted_ips'])}")
        else:
            click.echo(f"  Whitelisted IPs: {gcp_config['whitelisted_ips']}")
        click.echo(f"  Terraform State: {gcp_config.get('terraform_state', 'local')}")
        if gcp_config.get('terraform_state') == 'remote':
            click.echo(f"  State Project: {gcp_config.get('state_project')}")
            click.echo(f"  State Location: {gcp_config.get('state_location')}")
            click.echo(f"  State Bucket: {gcp_config.get('state_bucket')}")
        click.echo(f"  GKE Deployment Type: {gcp_config.get('gke_deployment_type', 'zonal')}")
        
        # Show advanced parameters if they exist
        if gcp_config.get('cidr_block'):
            click.echo(f"  CIDR Block: {gcp_config['cidr_block']}")
        if gcp_config.get('cluster_ipv4_cidr_block'):
            click.echo(f"  Cluster IPv4 CIDR: {gcp_config['cluster_ipv4_cidr_block']}")
        if gcp_config.get('services_ipv4_cidr_block'):
            click.echo(f"  Services IPv4 CIDR: {gcp_config['services_ipv4_cidr_block']}")
        if gcp_config.get('private_service_connect_cidr'):
            click.echo(f"  Private Service Connect CIDR: {gcp_config['private_service_connect_cidr']}")
        if gcp_config.get('lb_subnet_cidr'):
            click.echo(f"  Load Balancer Subnet CIDR: {gcp_config['lb_subnet_cidr']}")
        if gcp_config.get('kubernetes_version'):
            click.echo(f"  Kubernetes Version: {gcp_config['kubernetes_version']}")
        if gcp_config.get('gke_machine_type'):
            click.echo(f"  GKE Machine Type: {gcp_config['gke_machine_type']}")
        if gcp_config.get('gke_spot'):
            click.echo(f"  GKE Spot Instances: {gcp_config['gke_spot']}")
        if gcp_config.get('k8s_master_ipv4_cidr_block'):
            click.echo(f"  K8s Master IPv4 CIDR: {gcp_config['k8s_master_ipv4_cidr_block']}")
        if gcp_config.get('shared_host'):
            click.echo(f"  Shared Host: {gcp_config['shared_host']}")
        
        # Confirm execution
        if self.non_interactive:
            click.echo("🤖 Non-interactive mode: Proceeding with GCP infrastructure deployment")
        else:
            if safe_select("Proceed with GCP infrastructure deployment?", ['Yes', 'No']) == 'No':
                click.echo("❌ Infrastructure deployment cancelled")
                return False
        
        try:
            # Create a simple metadata collector for CLI usage
            class SimpleMetadataCollector:
                def __init__(self):
                    self.deployment_records = []
                
                def add_deployment_record(self, record):
                    click.echo(f"📝 Deployment record: {record}")
            
            # Create GoogleCloudManager instance directly
            gcp_manager = GoogleCloudManager(
                deployment=gcp_config['deployment'],
                billing_account_id=gcp_config['billing_account_id'],
                parent_folder=gcp_config['parent_folder'],
                customer=self.state.config['customer'],
                domain_name=self.state.config['domain_name'],
                admin_email=self.state.config['user_email'],
                whitelisted_ips=gcp_config['whitelisted_ips'],
                region=self.state.config['project_region'],
                project_id=gcp_config['project_id'],
                cloud_provider='gcp',
                cidr_block=gcp_config.get('cidr_block'),
                cluster_ipv4_cidr_block=gcp_config.get('cluster_ipv4_cidr_block'),
                services_ipv4_cidr_block=gcp_config.get('services_ipv4_cidr_block'),
                private_service_connect_cidr=gcp_config.get('private_service_connect_cidr'),
                lb_subnet_cidr=gcp_config.get('lb_subnet_cidr'),
                shared_host=gcp_config.get('shared_host'),
                kubernetes_version=gcp_config.get('kubernetes_version'),
                gke_machine_type=gcp_config.get('gke_machine_type'),
                gke_spot=gcp_config.get('gke_spot'),
                k8s_master_ipv4_cidr_block=gcp_config.get('k8s_master_ipv4_cidr_block'),
                terraform_state=gcp_config.get('terraform_state'),
                state_project=gcp_config.get('state_project'),
                state_location=gcp_config.get('state_location'),
                state_bucket=gcp_config.get('state_bucket'),
                gke_deployment_type=gcp_config.get('gke_deployment_type'),
                service_account_key=None,
                access_token=None,
                refresh_token=None,
                token_expiry=None,
                token_key=None,
                metadata_collector=SimpleMetadataCollector()
            )
            
            # Execute the deployment
            click.echo("🚀 Starting GCP infrastructure deployment...")
            result = gcp_manager.run()
            
            if "successfully" in result.lower():
                click.echo("✅ GCP infrastructure deployed successfully")
                
                # Set kubeconfig path for next steps
                self.state.kubeconfig_path = f"terraform/google_cloud/terragrunt/bi-platform/17-kubeconfig/kubeconfig"
                self.state.infrastructure_deployed = True
                self.state.save_state()
                return True
            else:
                click.echo(f"❌ GCP infrastructure deployment failed: {result}")
                return False
                
        except Exception as e:
            click.echo(f"❌ Error during GCP deployment: {str(e)}")
            return False

    def _collect_gcp_parameters(self) -> Dict:
        """Collect GCP-specific deployment parameters (only what's not in state)"""
        gcp_config = {}
        
        click.echo("\n📋 GCP Infrastructure Configuration")
        
        # Only ask for parameters that are not already in state
        if 'gcp_deployment_type' not in self.state.config:
            gcp_config['deployment'] = safe_select(
                "Select deployment type:",
                ['basic', 'advanced']
            )
            self.state.config['gcp_deployment_type'] = gcp_config['deployment']
        else:
            gcp_config['deployment'] = self.state.config['gcp_deployment_type']
        
        if 'gcp_billing_account_id' not in self.state.config:
            gcp_config['billing_account_id'] = safe_input(
                "Enter GCP billing account ID",
                validate=lambda text: len(text) > 0
            )
            self.state.config['gcp_billing_account_id'] = gcp_config['billing_account_id']
        else:
            gcp_config['billing_account_id'] = self.state.config['gcp_billing_account_id']
        
        if 'gcp_parent_folder' not in self.state.config:
            gcp_config['parent_folder'] = safe_input(
                "Enter GCP parent folder ID",
                validate=lambda text: len(text) > 0
            )
            self.state.config['gcp_parent_folder'] = gcp_config['parent_folder']
        else:
            gcp_config['parent_folder'] = self.state.config['gcp_parent_folder']
        
        if 'gcp_whitelisted_ips' not in self.state.config:
            whitelisted_ips_input = safe_input(
                "Enter whitelisted IP addresses (comma-separated, no quotes): 192.168.1.1/32,10.0.0.1/32",
                validate=lambda text: len(text) > 0
            )
            # Parse comma-separated IPs into a list (strict format, no quotes)
            whitelisted_ips_list = [ip.strip() for ip in whitelisted_ips_input.split(',') if ip.strip()]
            gcp_config['whitelisted_ips'] = whitelisted_ips_list
            self.state.config['gcp_whitelisted_ips'] = whitelisted_ips_list
        else:
            # Handle existing configuration - ensure it's a list
            existing_ips = self.state.config['gcp_whitelisted_ips']
            if isinstance(existing_ips, str):
                # Parse comma-separated string into list (strict format, no quotes)
                gcp_config['whitelisted_ips'] = [ip.strip() for ip in existing_ips.split(',') if ip.strip()]
            else:
                gcp_config['whitelisted_ips'] = existing_ips
        
        # Use default project ID format (fast-bi-{customer})
        gcp_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
        self.state.config['gcp_project_id'] = gcp_config['project_id']
        
        # State management configuration
        if 'gcp_terraform_state' not in self.state.config or not self.state.config.get('gcp_terraform_state'):
            click.echo("\n🏗️ State Management Configuration")
            click.echo("Choose the state backend type:")
            click.echo("  • LOCAL: Infrastructure files saved locally (no Fast.BI dependencies)")
            click.echo("  • REMOTE: Infrastructure files saved in GCS bucket (team collaboration)")
            
            gcp_config['terraform_state'] = safe_select(
                "Select Terraform state backend type:",
                ['local', 'remote']
            )
            self.state.config['gcp_terraform_state'] = gcp_config['terraform_state']
        else:
            gcp_config['terraform_state'] = self.state.config['gcp_terraform_state']
            click.echo(f"\n🏗️ State Management: Using existing configuration ({gcp_config['terraform_state']})")
        
        # Remote state configuration (only if remote is selected)
        if gcp_config['terraform_state'] == 'remote':
            if 'gcp_state_project' not in self.state.config:
                gcp_config['state_project'] = safe_input(
                    "Enter GCP project ID for remote state bucket:",
                    validate=lambda text: len(text) > 0
                )
                self.state.config['gcp_state_project'] = gcp_config['state_project']
            else:
                gcp_config['state_project'] = self.state.config['gcp_state_project']
            
            if 'gcp_state_location' not in self.state.config:
                gcp_config['state_location'] = safe_input(
                    "Enter GCS bucket location for remote state:",
                    validate=lambda text: len(text) > 0
                )
                self.state.config['gcp_state_location'] = gcp_config['state_location']
            else:
                gcp_config['state_location'] = self.state.config['gcp_state_location']
            
            if 'gcp_state_bucket' not in self.state.config:
                gcp_config['state_bucket'] = safe_input(
                    "Enter GCS bucket name for remote state:",
                    validate=lambda text: len(text) > 0
                )
                self.state.config['gcp_state_bucket'] = gcp_config['state_bucket']
            else:
                gcp_config['state_bucket'] = self.state.config['gcp_state_bucket']
            
            # Validate that all remote state parameters are provided
            if not gcp_config['state_project'] or not gcp_config['state_location'] or not gcp_config['state_bucket']:
                click.echo("❌ Error: All remote state parameters (state_project, state_location, state_bucket) are required when terraform_state=remote")
                return {}
        else:
            # For local state, set default values
            gcp_config['state_project'] = None
            gcp_config['state_location'] = None
            gcp_config['state_bucket'] = None
        
        # GKE deployment type
        if 'gcp_gke_deployment_type' not in self.state.config or not self.state.config.get('gcp_gke_deployment_type'):
            click.echo("\n🌐 GKE Deployment Type Configuration")
            click.echo("Choose the GKE deployment type:")
            click.echo("  • ZONAL: Single zone (cheaper, faster, good for demos/dev)")
            click.echo("  • MULTIZONE: Multi-zone (production-ready, better with spot instances)")
            
            gcp_config['gke_deployment_type'] = safe_select(
                "Select GKE deployment type:",
                ['zonal', 'multizone']
            )
            self.state.config['gcp_gke_deployment_type'] = gcp_config['gke_deployment_type']
        else:
            gcp_config['gke_deployment_type'] = self.state.config['gcp_gke_deployment_type']
            click.echo(f"\n🌐 GKE Deployment Type: Using existing configuration ({gcp_config['gke_deployment_type']})")
        
        # Inform about local state implications
        if gcp_config['terraform_state'] == 'local':
            click.echo("\n💾 Local State Configuration:")
            click.echo("   • Infrastructure files will be saved locally")
            click.echo("   • No dependencies on Fast.BI resources")
            click.echo("   • IMPORTANT: Keep infrastructure files safe!")
            click.echo("   • 'terraform destroy --all' may not work later")
            click.echo("   • Infrastructure updates will require manual reconfiguration")
            
            if safe_select("Continue with local state configuration?", ['Yes', 'No']) == 'No':
                return {}
        
        # Inform about GKE deployment type implications
        if gcp_config['gke_deployment_type'] == 'zonal':
            click.echo("\n🌐 Zonal GKE Configuration:")
            click.echo("   • Single zone deployment (cheaper/faster)")
            click.echo("   • Good for demos, development, and testing")
            click.echo("   • Lower cost (no master node charges)")
            click.echo("   • Faster deployment and teardown")
        elif gcp_config['gke_deployment_type'] == 'multizone':
            click.echo("\n🌐 Multizone GKE Configuration:")
            click.echo("   • Multi-zone deployment (production-ready)")
            click.echo("   • Better for production environments")
            click.echo("   • Scales better with spot instances")
            click.echo("   • Higher availability and stability")
            click.echo("   • Higher cost (master node charges apply)")
        
        # Optional advanced parameters (only for advanced deployment)
        if gcp_config['deployment'] == 'advanced':
            click.echo("\n🔧 Advanced Configuration")
            
            # CIDR blocks
            if 'gcp_cidr_block' not in self.state.config:
                if safe_select("Would you like to configure custom CIDR blocks?", ['Yes', 'No']) == 'Yes':
                    gcp_config['cidr_block'] = safe_input(
                        "Enter CIDR block for VPC",
                        default="10.0.0.0/16"
                    )
                    self.state.config['gcp_cidr_block'] = gcp_config['cidr_block']
            else:
                gcp_config['cidr_block'] = self.state.config['gcp_cidr_block']
            
            if 'gcp_cluster_ipv4_cidr_block' not in self.state.config:
                if safe_select("Would you like to configure cluster IPv4 CIDR block?", ['Yes', 'No']) == 'Yes':
                    gcp_config['cluster_ipv4_cidr_block'] = safe_input(
                        "Enter cluster IPv4 CIDR block",
                        default="10.1.0.0/16"
                    )
                    self.state.config['gcp_cluster_ipv4_cidr_block'] = gcp_config['cluster_ipv4_cidr_block']
            else:
                gcp_config['cluster_ipv4_cidr_block'] = self.state.config['gcp_cluster_ipv4_cidr_block']
            
            if 'gcp_services_ipv4_cidr_block' not in self.state.config:
                if safe_select("Would you like to configure services IPv4 CIDR block?", ['Yes', 'No']) == 'Yes':
                    gcp_config['services_ipv4_cidr_block'] = safe_input(
                        "Enter services IPv4 CIDR block",
                        default="10.2.0.0/16"
                    )
                    self.state.config['gcp_services_ipv4_cidr_block'] = gcp_config['services_ipv4_cidr_block']
            else:
                gcp_config['services_ipv4_cidr_block'] = self.state.config['gcp_services_ipv4_cidr_block']
            
            if 'gcp_private_service_connect_cidr' not in self.state.config:
                if safe_select("Would you like to configure private service connect CIDR?", ['Yes', 'No']) == 'Yes':
                    gcp_config['private_service_connect_cidr'] = safe_input(
                        "Enter private service connect CIDR",
                        default="10.3.0.0/16"
                    )
                    self.state.config['gcp_private_service_connect_cidr'] = gcp_config['private_service_connect_cidr']
            else:
                gcp_config['private_service_connect_cidr'] = self.state.config['gcp_private_service_connect_cidr']
            
            if 'gcp_lb_subnet_cidr' not in self.state.config:
                if safe_select("Would you like to configure load balancer subnet CIDR?", ['Yes', 'No']) == 'Yes':
                    gcp_config['lb_subnet_cidr'] = safe_input(
                        "Enter load balancer subnet CIDR",
                        default="10.4.0.0/16"
                    )
                    self.state.config['gcp_lb_subnet_cidr'] = gcp_config['lb_subnet_cidr']
            else:
                gcp_config['lb_subnet_cidr'] = self.state.config['gcp_lb_subnet_cidr']
            
            # Kubernetes configuration
            if 'gcp_kubernetes_version' not in self.state.config:
                if safe_select("Would you like to configure Kubernetes version?", ['Yes', 'No']) == 'Yes':
                    gcp_config['kubernetes_version'] = safe_input(
                        "Enter Kubernetes version",
                        default="1.28"
                    )
                    self.state.config['gcp_kubernetes_version'] = gcp_config['kubernetes_version']
            else:
                gcp_config['kubernetes_version'] = self.state.config['gcp_kubernetes_version']
            
            if 'gcp_gke_machine_type' not in self.state.config:
                if safe_select("Would you like to configure GKE machine type?", ['Yes', 'No']) == 'Yes':
                    gcp_config['gke_machine_type'] = safe_input(
                        "Enter GKE machine type",
                        default="e2-standard-4"
                    )
                    self.state.config['gcp_gke_machine_type'] = gcp_config['gke_machine_type']
            else:
                gcp_config['gke_machine_type'] = self.state.config['gcp_gke_machine_type']
            
            if 'gcp_gke_spot' not in self.state.config:
                if safe_select("Would you like to configure GKE spot instances?", ['Yes', 'No']) == 'Yes':
                    gcp_config['gke_spot'] = safe_select(
                        "Enable GKE spot instances?",
                        ['true', 'false']
                    )
                    self.state.config['gcp_gke_spot'] = gcp_config['gke_spot']
            else:
                gcp_config['gke_spot'] = self.state.config['gcp_gke_spot']
            
            if 'gcp_k8s_master_ipv4_cidr_block' not in self.state.config:
                if safe_select("Would you like to configure Kubernetes master IPv4 CIDR block?", ['Yes', 'No']) == 'Yes':
                    gcp_config['k8s_master_ipv4_cidr_block'] = safe_input(
                        "Enter Kubernetes master IPv4 CIDR block",
                        default="172.16.0.0/28"
                    )
                    self.state.config['gcp_k8s_master_ipv4_cidr_block'] = gcp_config['k8s_master_ipv4_cidr_block']
            else:
                gcp_config['k8s_master_ipv4_cidr_block'] = self.state.config['gcp_k8s_master_ipv4_cidr_block']
            
            # Shared host configuration
            if 'gcp_shared_host' not in self.state.config:
                if safe_select("Would you like to configure shared host?", ['Yes', 'No']) == 'Yes':
                    gcp_config['shared_host'] = safe_input(
                        "Enter shared host configuration"
                    )
                    self.state.config['gcp_shared_host'] = gcp_config['shared_host']
            else:
                gcp_config['shared_host'] = self.state.config['gcp_shared_host']
        else:
            click.echo("\n✅ Using default configuration for basic deployment")
        
        return gcp_config

    def _deploy_onprem_infrastructure(self) -> bool:
        """Deploy on-premise infrastructure by collecting kubeconfig and storage class"""
        click.echo("🔧 Configuring on-premise infrastructure...")
        
        # Collect on-premise specific parameters
        onprem_config = self._collect_onprem_parameters()
        
        if not onprem_config:
            click.echo("❌ On-premise configuration cancelled")
            return False
        
        # Show deployment configuration
        click.echo(f"\n📋 On-Premise Infrastructure Configuration:")
        click.echo(f"  Customer: {self.state.config['customer']}")
        click.echo(f"  Domain: {self.state.config['domain_name']}")
        click.echo(f"  Admin Email: {self.state.config['user_email']}")
        click.echo(f"  Kubeconfig Path: {onprem_config['kubeconfig_path']}")
        click.echo(f"  Cluster Name: {onprem_config['cluster_name']}")
        click.echo(f"  Storage Class: {onprem_config['storage_class']}")
        
        # Confirm execution
        if self.non_interactive:
            click.echo("🤖 Non-interactive mode: Proceeding with on-premise infrastructure configuration")
        else:
            if safe_select("Proceed with on-premise infrastructure configuration?", ['Yes', 'No']) == 'No':
                click.echo("❌ On-premise infrastructure configuration cancelled")
                return False
        
        try:
            # Verify kubeconfig is valid
            result = subprocess.run(
                ["kubectl", "--kubeconfig", onprem_config['kubeconfig_path'], "cluster-info"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                click.echo("✅ Kubeconfig is valid and cluster is accessible")
                
                # Set kubeconfig path for next steps
                self.state.kubeconfig_path = onprem_config['kubeconfig_path']
                self.state.infrastructure_deployed = True
                self.state.save_state()
                return True
            else:
                click.echo(f"❌ Invalid kubeconfig: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            click.echo("❌ Timeout connecting to cluster")
            return False
        except Exception as e:
            click.echo(f"❌ Error validating kubeconfig: {str(e)}")
            return False

    def _collect_onprem_parameters(self) -> Dict:
        """Collect on-premise specific deployment parameters"""
        onprem_config = {}
        
        click.echo("\n📋 On-Premise Infrastructure Configuration")
        
        # Kubeconfig path
        if 'onprem_kubeconfig_path' not in self.state.config:
            onprem_config['kubeconfig_path'] = safe_input(
                "Enter path to kubeconfig file",
                validate=lambda path: Path(path).exists()
            )
            self.state.config['onprem_kubeconfig_path'] = onprem_config['kubeconfig_path']
        else:
            onprem_config['kubeconfig_path'] = self.state.config['onprem_kubeconfig_path']
        
        # Cluster name
        if 'onprem_cluster_name' not in self.state.config:
            onprem_config['cluster_name'] = safe_input(
                "Enter cluster name",
                default=f"fast-bi-{self.state.config['customer']}-cluster"
            )
            self.state.config['onprem_cluster_name'] = onprem_config['cluster_name']
        else:
            onprem_config['cluster_name'] = self.state.config['onprem_cluster_name']
        
        # Storage class
        if 'onprem_storage_class' not in self.state.config:
            onprem_config['storage_class'] = safe_input(
                "Enter storage class name",
                default="local-storage"
            )
            self.state.config['onprem_storage_class'] = onprem_config['storage_class']
        else:
            onprem_config['storage_class'] = self.state.config['onprem_storage_class']
        
        return onprem_config

    def _collect_secrets_parameters(self) -> Dict:
        """Collect parameters needed for secrets generation"""
        secrets_config = {}
        
        click.echo("\n🔐 Secrets Generation Configuration")
        
        # Vault method
        if 'secrets_vault_method' not in self.state.config:
            secrets_config['vault_method'] = safe_select(
                "Select vault method:",
                ['local_vault', 'external_infisical']
            )
            self.state.config['secrets_vault_method'] = secrets_config['vault_method']
        else:
            secrets_config['vault_method'] = self.state.config['secrets_vault_method']
        
        # Data analysis platform
        if 'secrets_data_analysis_platform' not in self.state.config:
            secrets_config['data_analysis_platform'] = safe_select(
                "Select data analysis platform:",
                ['lightdash', 'superset', 'metabase', 'looker']
            )
            self.state.config['secrets_data_analysis_platform'] = secrets_config['data_analysis_platform']
        else:
            secrets_config['data_analysis_platform'] = self.state.config['secrets_data_analysis_platform']
        
        # Data warehouse platform
        if 'secrets_data_warehouse_platform' not in self.state.config:
            secrets_config['data_warehouse_platform'] = safe_select(
                "Select data warehouse platform:",
                ['bigquery', 'snowflake', 'redshift']
            )
            self.state.config['secrets_data_warehouse_platform'] = secrets_config['data_warehouse_platform']
        else:
            secrets_config['data_warehouse_platform'] = self.state.config['secrets_data_warehouse_platform']
        
        # Cloud provider specific configuration
        cloud_provider = self.state.config.get('cloud_provider', 'gcp')
        
        # Project ID and cloud-specific settings
        if cloud_provider == 'gcp':
            if 'gcp_project_id' in self.state.config:
                secrets_config['project_id'] = self.state.config['gcp_project_id']
                secrets_config['bigquery_project_id'] = self.state.config['gcp_project_id']
            else:
                secrets_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
                secrets_config['bigquery_project_id'] = f"fast-bi-{self.state.config['customer']}"
            
            # GCP Service account JSON files - only required if BigQuery is selected
            if secrets_config['data_warehouse_platform'] == 'bigquery':
                if 'secrets_data_platform_sa_json' not in self.state.config:
                    # For GCP infrastructure, automatically use the service account keys from infrastructure deployment
                    if self.state.config.get('cloud_provider') == 'gcp':
                        # Try to read from the expected locations from infrastructure deployment
                        data_platform_sa_path = "terraform/google_cloud/terragrunt/bi-platform/08-dbt_deploy_sa/sa_key.txt"
                        data_analysis_sa_path = "terraform/google_cloud/terragrunt/bi-platform/15-bi_data_sa/sa_key.txt"
                        
                        try:
                            with open(data_platform_sa_path, 'r') as f:
                                secrets_config['data_platform_sa_json'] = f.read().strip()
                            with open(data_analysis_sa_path, 'r') as f:
                                secrets_config['data_analysis_sa_json'] = f.read().strip()
                            
                            # Save to state
                            self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                            self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                            click.echo("✅ GCP service account keys automatically loaded from infrastructure deployment")
                            click.echo("   • Data Platform SA: 08-dbt_deploy_sa/sa_key.txt")
                            click.echo("   • Data Analysis SA: 15-bi_data_sa/sa_key.txt")
                        except FileNotFoundError:
                            click.echo("⚠️ GCP service account keys not found from infrastructure deployment")
                            click.echo("Please provide paths to Google Cloud service account JSON files:")
                            
                            # Ask for file paths
                            data_platform_sa_file = safe_input(
                                "Enter path to GCP service account JSON file for data platform:",
                                validate=lambda x: len(x) > 0 and Path(x).exists()
                            )
                            data_analysis_sa_file = safe_input(
                                "Enter path to GCP service account JSON file for data analysis:",
                                validate=lambda x: len(x) > 0 and Path(x).exists()
                            )
                            
                            # Read and encode files to base64
                            try:
                                with open(data_platform_sa_file, 'r') as f:
                                    import base64
                                    secrets_config['data_platform_sa_json'] = base64.b64encode(f.read().encode()).decode()
                                with open(data_analysis_sa_file, 'r') as f:
                                    secrets_config['data_analysis_sa_json'] = base64.b64encode(f.read().encode()).decode()
                                
                                # Save to state
                                self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                                self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                                click.echo("✅ GCP service account files loaded and encoded to base64")
                            except Exception as e:
                                click.echo(f"❌ Error reading service account files: {str(e)}")
                                return {}
                    else:
                        # For non-GCP infrastructure, ask for service account files
                        click.echo("🔐 GCP Service Account Configuration (BigQuery requires GCP service account)")
                        click.echo("Please provide paths to Google Cloud service account JSON files:")
                        
                        # Ask for file paths
                        data_platform_sa_file = safe_input(
                            "Enter path to GCP service account JSON file for data platform:",
                            validate=lambda x: len(x) > 0 and Path(x).exists()
                        )
                        data_analysis_sa_file = safe_input(
                            "Enter path to GCP service account JSON file for data analysis:",
                            validate=lambda x: len(x) > 0 and Path(x).exists()
                        )
                        
                        # Read and encode files to base64
                        try:
                            with open(data_platform_sa_file, 'r') as f:
                                import base64
                                secrets_config['data_platform_sa_json'] = base64.b64encode(f.read().encode()).decode()
                            with open(data_analysis_sa_file, 'r') as f:
                                secrets_config['data_analysis_sa_json'] = base64.b64encode(f.read().encode()).decode()
                            
                            # Save to state
                            self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                            self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                            click.echo("✅ GCP service account files loaded and encoded to base64")
                        except Exception as e:
                            click.echo(f"❌ Error reading service account files: {str(e)}")
                            return {}
                else:
                    secrets_config['data_platform_sa_json'] = self.state.config['secrets_data_platform_sa_json']
                    secrets_config['data_analysis_sa_json'] = self.state.config['secrets_data_analysis_sa_json']

                # Ensure BigQuery project and region are set for GCP
                # Project ID: prefer explicit YAML value, otherwise fall back to GCP project id
                if self.state.config.get('secrets_bigquery_project_id'):
                    secrets_config['bigquery_project_id'] = self.state.config['secrets_bigquery_project_id']
                else:
                    secrets_config['bigquery_project_id'] = secrets_config.get('bigquery_project_id') or self.state.config.get('gcp_project_id') or f"fast-bi-{self.state.config['customer']}"
                    self.state.config['secrets_bigquery_project_id'] = secrets_config['bigquery_project_id']

                # Region: prefer explicit YAML value, otherwise use deployment project_region
                if self.state.config.get('secrets_bigquery_region'):
                    secrets_config['bigquery_region'] = self.state.config['secrets_bigquery_region']
                else:
                    secrets_config['bigquery_region'] = self.state.config.get('project_region', 'us-central1')
                    self.state.config['secrets_bigquery_region'] = secrets_config['bigquery_region']
            else:
                # Not BigQuery, no GCP service account needed
                click.echo("ℹ️ GCP service account not required (not using BigQuery)")
                secrets_config['data_platform_sa_json'] = ""
                secrets_config['data_analysis_sa_json'] = ""
        
        elif cloud_provider == 'aws':
            # AWS configuration
            secrets_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
            secrets_config['bigquery_project_id'] = f"fast-bi-{self.state.config['customer']}"
            
            # Service account credentials - depends on data warehouse choice
            if secrets_config['data_warehouse_platform'] == 'bigquery':
                # BigQuery requires GCP service accounts and project details (even when deploying on AWS)
                if 'secrets_data_platform_sa_json' not in self.state.config:
                    click.echo("🔐 GCP Service Account Configuration (BigQuery requires GCP service account)")
                    click.echo("Please provide paths to Google Cloud service account JSON files:")
                    
                    # Ask for file paths
                    data_platform_sa_file = safe_input(
                        "Enter path to GCP service account JSON file for data platform:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    data_analysis_sa_file = safe_input(
                        "Enter path to GCP service account JSON file for data analysis:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    
                    # Read and encode files to base64
                    try:
                        with open(data_platform_sa_file, 'r') as f:
                            import base64
                            secrets_config['data_platform_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        with open(data_analysis_sa_file, 'r') as f:
                            secrets_config['data_analysis_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        
                        # Save to state
                        self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                        self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                        click.echo("✅ GCP service account files loaded and encoded to base64")
                    except Exception as e:
                        click.echo(f"❌ Error reading service account files: {str(e)}")
                        return {}
                
                # Collect BigQuery-specific parameters
                click.echo("🔧 BigQuery Configuration (required for BigQuery data warehouse)")
                
                # BigQuery Project ID
                if 'secrets_bigquery_project_id' not in self.state.config:
                    bigquery_project_id = safe_input(
                        "Enter BigQuery project ID:",
                        default=f"fast-bi-{self.state.config['customer']}"
                    )
                    secrets_config['bigquery_project_id'] = bigquery_project_id
                    self.state.config['secrets_bigquery_project_id'] = bigquery_project_id
                else:
                    secrets_config['bigquery_project_id'] = self.state.config['secrets_bigquery_project_id']
                
                # BigQuery Region
                if 'secrets_bigquery_region' not in self.state.config:
                    bigquery_region = safe_input(
                        "Enter BigQuery region:",
                        default="us-central1"
                    )
                    secrets_config['bigquery_region'] = bigquery_region
                    self.state.config['secrets_bigquery_region'] = bigquery_region
                else:
                    secrets_config['bigquery_region'] = self.state.config['secrets_bigquery_region']
                
                click.echo("✅ BigQuery configuration completed")
            
            elif secrets_config['data_warehouse_platform'] in ['snowflake', 'redshift']:
                # Snowflake/Redshift require AWS credentials
                if 'secrets_data_platform_sa_json' not in self.state.config:
                    click.echo(f"🔐 AWS Credentials Configuration ({secrets_config['data_warehouse_platform'].title()} requires AWS credentials)")
                    click.echo("Please provide paths to AWS credential files:")
                    
                    # Ask for file paths
                    data_platform_sa_file = safe_input(
                        "Enter path to AWS credentials file for data platform:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    data_analysis_sa_file = safe_input(
                        "Enter path to AWS credentials file for data analysis:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    
                    # Read and encode files to base64
                    try:
                        with open(data_platform_sa_file, 'r') as f:
                            import base64
                            secrets_config['data_platform_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        with open(data_analysis_sa_file, 'r') as f:
                            secrets_config['data_analysis_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        
                        # Save to state
                        self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                        self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                        click.echo("✅ AWS credential files loaded and encoded to base64")
                    except Exception as e:
                        click.echo(f"❌ Error reading credential files: {str(e)}")
                        return {}
                else:
                    secrets_config['data_platform_sa_json'] = self.state.config['secrets_data_platform_sa_json']
                    secrets_config['data_analysis_sa_json'] = self.state.config['secrets_data_analysis_sa_json']
            else:
                # Unknown data warehouse
                click.echo(f"⚠️ Unknown data warehouse: {secrets_config['data_warehouse_platform']}")
                secrets_config['data_platform_sa_json'] = ""
                secrets_config['data_analysis_sa_json'] = ""
        
        elif cloud_provider == 'azure':
            # Azure configuration
            secrets_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
            secrets_config['bigquery_project_id'] = f"fast-bi-{self.state.config['customer']}"
            
            # Azure Service Principal credentials - only required if BigQuery is selected
            if secrets_config['data_warehouse_platform'] == 'bigquery':
                if 'secrets_data_platform_sa_json' not in self.state.config:
                    click.echo("🔐 Azure Service Principal Configuration (BigQuery requires Azure service principal)")
                    click.echo("Please provide paths to Azure service principal credential files:")
                    
                    # Ask for file paths
                    data_platform_sa_file = safe_input(
                        "Enter path to Azure service principal credentials file for data platform:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    data_analysis_sa_file = safe_input(
                        "Enter path to Azure service principal credentials file for data analysis:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    
                    # Read and encode files to base64
                    try:
                        with open(data_platform_sa_file, 'r') as f:
                            import base64
                            secrets_config['data_platform_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        with open(data_analysis_sa_file, 'r') as f:
                            secrets_config['data_analysis_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        
                        # Save to state
                        self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                        self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                        click.echo("✅ Azure service principal files loaded and encoded to base64")
                    except Exception as e:
                        click.echo(f"❌ Error reading service principal files: {str(e)}")
                        return {}
                else:
                    secrets_config['data_platform_sa_json'] = self.state.config['secrets_data_platform_sa_json']
                    secrets_config['data_analysis_sa_json'] = self.state.config['secrets_data_analysis_sa_json']
            else:
                # Not BigQuery, no Azure service principal needed
                click.echo("ℹ️ Azure service principal not required (not using BigQuery)")
                secrets_config['data_platform_sa_json'] = ""
                secrets_config['data_analysis_sa_json'] = ""
        
        elif cloud_provider == 'onprem':
            # On-premise configuration
            secrets_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
            secrets_config['bigquery_project_id'] = f"fast-bi-{self.state.config['customer']}"
            
            # On-premise deployments can still use BigQuery as data warehouse
            if secrets_config['data_warehouse_platform'] == 'bigquery':
                if 'secrets_data_platform_sa_json' not in self.state.config:
                    click.echo("🔐 GCP Service Account Configuration (BigQuery requires GCP service account)")
                    click.echo("Please provide paths to Google Cloud service account JSON files:")
                    
                    # Ask for file paths
                    data_platform_sa_file = safe_input(
                        "Enter path to GCP service account JSON file for data platform:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    data_analysis_sa_file = safe_input(
                        "Enter path to GCP service account JSON file for data analysis:",
                        validate=lambda x: len(x) > 0 and Path(x).exists()
                    )
                    
                    # Read and encode files to base64
                    try:
                        with open(data_platform_sa_file, 'r') as f:
                            import base64
                            secrets_config['data_platform_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        with open(data_analysis_sa_file, 'r') as f:
                            secrets_config['data_analysis_sa_json'] = base64.b64encode(f.read().encode()).decode()
                        
                        # Save to state
                        self.state.config['secrets_data_platform_sa_json'] = secrets_config['data_platform_sa_json']
                        self.state.config['secrets_data_analysis_sa_json'] = secrets_config['data_analysis_sa_json']
                        click.echo("✅ GCP service account files loaded and encoded to base64")
                    except Exception as e:
                        click.echo(f"❌ Error reading service account files: {str(e)}")
                        return {}
                else:
                    secrets_config['data_platform_sa_json'] = self.state.config['secrets_data_platform_sa_json']
                    secrets_config['data_analysis_sa_json'] = self.state.config['secrets_data_analysis_sa_json']
                
                # Collect BigQuery-specific parameters
                click.echo("🔧 BigQuery Configuration (required for BigQuery data warehouse)")
                
                # BigQuery Project ID
                if 'secrets_bigquery_project_id' not in self.state.config:
                    bigquery_project_id = safe_input(
                        "Enter BigQuery project ID:",
                        default=f"fast-bi-{self.state.config['customer']}"
                    )
                    secrets_config['bigquery_project_id'] = bigquery_project_id
                    self.state.config['secrets_bigquery_project_id'] = bigquery_project_id
                else:
                    secrets_config['bigquery_project_id'] = self.state.config['secrets_bigquery_project_id']
                
                # BigQuery Region
                if 'secrets_bigquery_region' not in self.state.config:
                    bigquery_region = safe_input(
                        "Enter BigQuery region:",
                        default="us-central1"
                    )
                    secrets_config['bigquery_region'] = bigquery_region
                    self.state.config['secrets_bigquery_region'] = bigquery_region
                else:
                    secrets_config['bigquery_region'] = self.state.config['secrets_bigquery_region']
                
                click.echo("✅ BigQuery configuration completed")
            else:
                # Not BigQuery, no service account needed for on-premise
                click.echo("ℹ️ No cloud service account required for on-premise deployment (not using BigQuery)")
                secrets_config['data_platform_sa_json'] = ""
                secrets_config['data_analysis_sa_json'] = ""
        
        else:
            click.echo(f"⚠️ Unsupported cloud provider: {cloud_provider}")
            return {}
        
        # Git configuration
        if 'secrets_git_provider' not in self.state.config:
            secrets_config['git_provider'] = safe_select(
                "Select Git provider:",
                ['github', 'gitlab', 'bitbucket', 'fastbi']
            )
            self.state.config['secrets_git_provider'] = secrets_config['git_provider']
        else:
            secrets_config['git_provider'] = self.state.config['secrets_git_provider']
        
        if 'secrets_dag_repo_url' not in self.state.config:
            while True:
                try:
                    dag_repo_url = safe_input("Enter DAG repository URL:")
                    # Validate and normalize the URL based on access method
                    secrets_config['dag_repo_url'] = validate_and_normalize_repo_url(dag_repo_url, secrets_config['repo_access_method'])
                    self.state.config['secrets_dag_repo_url'] = secrets_config['dag_repo_url']
                    break
                except ValueError as e:
                    click.echo(f"❌ {e}")
                    click.echo("Please enter a valid repository URL (e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git)")
        else:
            secrets_config['dag_repo_url'] = self.state.config['secrets_dag_repo_url']
        
        if 'secrets_data_repo_url' not in self.state.config:
            while True:
                try:
                    data_repo_url = safe_input("Enter data repository URL:")
                    # Validate and normalize the URL based on access method
                    secrets_config['data_repo_url'] = validate_and_normalize_repo_url(data_repo_url, secrets_config['repo_access_method'])
                    self.state.config['secrets_data_repo_url'] = secrets_config['data_repo_url']
                    break
                except ValueError as e:
                    click.echo(f"❌ {e}")
                    click.echo("Please enter a valid repository URL (e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git)")
        else:
            secrets_config['data_repo_url'] = self.state.config['secrets_data_repo_url']
        
        if 'secrets_data_repo_main_branch' not in self.state.config:
            secrets_config['data_repo_main_branch'] = safe_input(
                "Enter data repository main branch:",
                default="main"
            )
            self.state.config['secrets_data_repo_main_branch'] = secrets_config['data_repo_main_branch']
        else:
            secrets_config['data_repo_main_branch'] = self.state.config['secrets_data_repo_main_branch']
        
        if 'secrets_repo_access_method' not in self.state.config:
            secrets_config['repo_access_method'] = safe_select(
                "Select repository access method:",
                ['access_token', 'deploy_keys', 'ssh_keys']
            )
            self.state.config['secrets_repo_access_method'] = secrets_config['repo_access_method']
        else:
            secrets_config['repo_access_method'] = self.state.config['secrets_repo_access_method']
        
        if 'secrets_git_provider_access_token' not in self.state.config:
            if safe_select("Configure Git access token?", ['Yes', 'No']) == 'Yes':
                secrets_config['git_provider_access_token'] = safe_input(
                    "Enter Git provider access token:"
                )
                self.state.config['secrets_git_provider_access_token'] = secrets_config['git_provider_access_token']
        else:
            secrets_config['git_provider_access_token'] = self.state.config['secrets_git_provider_access_token']
        
        # SMTP configuration (optional)
        if 'secrets_smtp_host' not in self.state.config:
            if safe_select("Configure SMTP settings?", ['Yes', 'No']) == 'Yes':
                secrets_config['smtp_host'] = safe_input("Enter SMTP host:")
                secrets_config['smtp_port'] = safe_input("Enter SMTP port:")
                secrets_config['smtp_username'] = safe_input("Enter SMTP username:")
                secrets_config['smtp_password'] = safe_input("Enter SMTP password:")
                
                self.state.config['secrets_smtp_host'] = secrets_config['smtp_host']
                self.state.config['secrets_smtp_port'] = secrets_config['smtp_port']
                self.state.config['secrets_smtp_username'] = secrets_config['smtp_username']
                self.state.config['secrets_smtp_password'] = secrets_config['smtp_password']
        else:
            secrets_config['smtp_host'] = self.state.config['secrets_smtp_host']
            secrets_config['smtp_port'] = self.state.config['secrets_smtp_port']
            secrets_config['smtp_username'] = self.state.config['secrets_smtp_username']
            secrets_config['smtp_password'] = self.state.config['secrets_smtp_password']
        
        # Orchestrator platform
        if 'secrets_orchestrator_platform' not in self.state.config:
            secrets_config['orchestrator_platform'] = safe_select(
                "Select orchestrator platform:",
                ['Airflow', 'Composer']
            )
            self.state.config['secrets_orchestrator_platform'] = secrets_config['orchestrator_platform']
        else:
            secrets_config['orchestrator_platform'] = self.state.config['secrets_orchestrator_platform']
        
        return secrets_config

    def _display_deploy_keys_for_repositories(self):
        """Read and display public keys for repository configuration"""
        try:
            # Read the vault structure file
            vault_file = f"/tmp/{self.state.config['customer']}_customer_vault_structure.json"
            
            if not Path(vault_file).exists():
                click.echo("⚠️ Vault structure file not found")
                return
            
            with open(vault_file, 'r') as f:
                vault_data = json.load(f)
            
            # Extract public keys
            data_platform_runner = vault_data.get('data-platform-runner', {})
            
            # Data orchestrator repository public key
            orchestrator_keys = data_platform_runner.get('ssh-keys-data-orchestrator-repo', {})
            orchestrator_public_key = orchestrator_keys.get('public', '')
            
            # Data model repository public key
            data_model_keys = data_platform_runner.get('ssh-keys-data-model-repo', {})
            data_model_public_key = data_model_keys.get('public', '')
            
            if orchestrator_public_key or data_model_public_key:
                click.echo("\n🔑 DEPLOY KEYS FOR REPOSITORY CONFIGURATION")
                click.echo("=" * 50)
                click.echo("Please add these public keys as deploy keys in your repositories:")
                click.echo("")
                
                if orchestrator_public_key:
                    click.echo("📁 DAG Repository Deploy Key:")
                    click.echo(f"Repository: {self.state.config.get('secrets_dag_repo_url', 'Not configured')}")
                    click.echo("Public Key:")
                    click.echo(orchestrator_public_key)
                    click.echo("")
                
                if data_model_public_key:
                    click.echo("📁 Data Repository Deploy Key:")
                    click.echo(f"Repository: {self.state.config.get('secrets_data_repo_url', 'Not configured')}")
                    click.echo("Public Key:")
                    click.echo(data_model_public_key)
                    click.echo("")
                
                click.echo("=" * 50)
                click.echo("⚠️ IMPORTANT: Add these deploy keys to your repositories before proceeding to Phase 3")
                click.echo("")
        
        except Exception as e:
            click.echo(f"⚠️ Error reading deploy keys: {str(e)}")

    def _verify_deploy_keys_configured(self) -> bool:
        """Verify that deploy keys are configured in repositories"""
        click.echo("\n🔍 Verifying deploy keys configuration...")
        
        # For now, we'll ask the user to confirm they've added the deploy keys
        # In a real implementation, you might want to test the connection to the repositories
        confirmation = safe_select(
            "Have you added the deploy keys to your repositories?",
            ['Yes', 'No']
        )
        
        if confirmation == 'Yes':
            click.echo("✅ Deploy keys verification confirmed")
            return True
        else:
            click.echo("❌ Please add the deploy keys to your repositories first")
            return False

    def _verify_dns_nameserver_configuration(self) -> bool:
        """Verify DNS nameserver configuration for custom domains"""
        domain_name = self.state.config.get('domain_name', '')
        customer = self.state.config.get('customer', '')
        
        # Check if this is a custom domain (not ending with fast.bi)
        if domain_name.endswith('fast.bi'):
            click.echo("✅ Using fast.bi domain - DNS nameserver configuration handled automatically by Terraform")
            return True
        
        # For custom domains, check if DNS nameservers file exists
        dns_nameservers_path = "terraform/google_cloud/terragrunt/bi-platform/05-create-dns-zone/dns_zone_nameservers.txt"
        
        if not Path(dns_nameservers_path).exists():
            click.echo("⚠️ DNS nameservers file not found. Skipping DNS verification.")
            return True
        
        # Read nameservers from file
        try:
            with open(dns_nameservers_path, 'r') as f:
                nameservers = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            click.echo(f"⚠️ Error reading DNS nameservers file: {str(e)}")
            return True
        
        if not nameservers:
            click.echo("⚠️ No nameservers found in DNS file. Skipping DNS verification.")
            return True
        
        # Display DNS configuration instructions
        click.echo("\n🌐 DNS NAMESERVER CONFIGURATION REQUIRED")
        click.echo("=" * 50)
        click.echo(f"Domain: {customer}.{domain_name}")
        click.echo("")
        click.echo("IMPORTANT: You must configure DNS nameserver records for your domain.")
        click.echo("This is required for the platform to work correctly.")
        click.echo("")
        click.echo("📋 DNS Configuration Instructions:")
        click.echo("1. Log into your domain registrar's DNS management console")
        click.echo(f"2. Find the DNS settings for: {customer}.{domain_name}")
        click.echo("3. Configure the following nameserver records:")
        click.echo("")
        
        for i, nameserver in enumerate(nameservers, 1):
            click.echo(f"   NS Record {i}: {nameserver}")
        
        click.echo("")
        click.echo("4. Save the DNS configuration")
        click.echo("5. Wait for DNS propagation")
        click.echo("")
        click.echo("⚠️ NOTE: The platform will not work correctly until DNS is properly configured.")
        click.echo("")
        
        # Ask user to confirm DNS configuration
        confirmation = safe_select(
            "Have you configured the DNS nameserver records?",
            [
                "Yes, DNS is configured and ready",
                "No, I need to configure DNS first",
                "Skip DNS verification (not recommended)"
            ]
        )
        
        if confirmation == "Yes, DNS is configured and ready":
            click.echo("✅ DNS nameserver configuration verified")
            return True
        elif confirmation == "No, I need to configure DNS first":
            click.echo("⚠️ Please configure DNS nameserver records before proceeding.")
            click.echo("   The platform requires proper DNS configuration to function correctly.")
            return False
        else:  # Skip verification
            click.echo("⚠️ Skipping DNS verification (platform may not work correctly)")
            return True

    def _collect_repository_parameters(self) -> Dict:
        """Collect parameters needed for repository configuration"""
        repo_config = {}
        
        click.echo("\n📚 Repository Configuration")
        
        # Use existing configuration from Phase 2
        repo_config['git_provider'] = self.state.config.get('secrets_git_provider', 'fastbi')
        repo_config['dag_repo_url'] = self.state.config.get('secrets_dag_repo_url', '')
        repo_config['data_repo_url'] = self.state.config.get('secrets_data_repo_url', '')
        repo_config['data_repo_main_branch'] = self.state.config.get('secrets_data_repo_main_branch', 'main')
        repo_config['repo_access_method'] = self.state.config.get('secrets_repo_access_method', 'deploy_keys')
        repo_config['git_provider_access_token'] = self.state.config.get('secrets_git_provider_access_token', '')
        
        # Use project ID from infrastructure
        if 'gcp_project_id' in self.state.config:
            repo_config['project_id'] = self.state.config['gcp_project_id']
            repo_config['bigquery_project_id'] = self.state.config['gcp_project_id']
        else:
            repo_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
            repo_config['bigquery_project_id'] = f"fast-bi-{self.state.config['customer']}"
        
        # Use platform configurations from Phase 2
        repo_config['data_analysis_platform'] = self.state.config.get('secrets_data_analysis_platform', 'lightdash')
        repo_config['data_warehouse_platform'] = self.state.config.get('secrets_data_warehouse_platform', 'bigquery')
        repo_config['orchestrator_platform'] = self.state.config.get('secrets_orchestrator_platform', 'Airflow')
        
        # Display current configuration
        click.echo("📋 Current Repository Configuration:")
        click.echo(f"  Git Provider: {repo_config['git_provider']}")
        click.echo(f"  DAG Repository: {repo_config['dag_repo_url']}")
        click.echo(f"  Data Repository: {repo_config['data_repo_url']}")
        click.echo(f"  Data Repository Branch: {repo_config['data_repo_main_branch']}")
        click.echo(f"  Access Method: {repo_config['repo_access_method']}")
        click.echo(f"  Data Analysis Platform: {repo_config['data_analysis_platform']}")
        click.echo(f"  Data Warehouse Platform: {repo_config['data_warehouse_platform']}")
        click.echo(f"  Orchestrator Platform: {repo_config['orchestrator_platform']}")
        
        # Confirm repository configuration
        if safe_select("Proceed with repository configuration?", ['Yes', 'No']) == 'No':
            click.echo("❌ Repository configuration cancelled")
            return {}
        
        # Ask if user wants to modify any settings
        if safe_select("Would you like to modify any repository settings?", ['Yes', 'No']) == 'Yes':
            # Allow modification of key settings
            if safe_select("Modify DAG repository URL?", ['Yes', 'No']) == 'Yes':
                while True:
                    try:
                        dag_repo_url = safe_input("Enter new DAG repository URL:")
                        repo_config['dag_repo_url'] = validate_and_normalize_repo_url(dag_repo_url, repo_config['repo_access_method'])
                        self.state.config['secrets_dag_repo_url'] = repo_config['dag_repo_url']
                        break
                    except ValueError as e:
                        click.echo(f"❌ {e}")
                        click.echo("Please enter a valid repository URL (e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git)")
            
            if safe_select("Modify data repository URL?", ['Yes', 'No']) == 'Yes':
                while True:
                    try:
                        data_repo_url = safe_input("Enter new data repository URL:")
                        repo_config['data_repo_url'] = validate_and_normalize_repo_url(data_repo_url, repo_config['repo_access_method'])
                        self.state.config['secrets_data_repo_url'] = repo_config['data_repo_url']
                        break
                    except ValueError as e:
                        click.echo(f"❌ {e}")
                        click.echo("Please enter a valid repository URL (e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git)")
            
            if safe_select("Modify data repository main branch?", ['Yes', 'No']) == 'Yes':
                repo_config['data_repo_main_branch'] = safe_input("Enter new main branch:", default="main")
                self.state.config['secrets_data_repo_main_branch'] = repo_config['data_repo_main_branch']
        
        return repo_config

    def _collect_infrastructure_services_parameters(self) -> Dict:
        """Collect parameters needed for infrastructure services deployment"""
        infra_config = {}
        
        click.echo("\n🔧 Infrastructure Services Configuration")
        
        # Use project ID from infrastructure
        if 'gcp_project_id' in self.state.config:
            infra_config['project_id'] = self.state.config['gcp_project_id']
        else:
            infra_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
        
        # Collect missing parameters for specific services
        click.echo("📋 Collecting additional parameters for infrastructure services...")
        
        # External IP for Traefik (can be from terraform or user input)
        if 'infra_external_ip' not in self.state.config:
            external_ip_path = "terraform/google_cloud/terragrunt/bi-platform/04-external-ip-traefik/external_ip_traefik.txt"
            if Path(external_ip_path).exists():
                with open(external_ip_path, 'r') as f:
                    default_external_ip = f.read().strip()
                click.echo(f"✅ External IP found from infrastructure: {default_external_ip}")
                infra_config['external_ip'] = default_external_ip
                self.state.config['infra_external_ip'] = default_external_ip
            else:
                # Allow user to provide custom external IP if not found
                custom_ip = safe_input(
                    "External IP not found from infrastructure. Enter custom external IP for Traefik load balancer (or press Enter to skip):",
                    default=""
                )
                if custom_ip.strip():
                    infra_config['external_ip'] = custom_ip
                    self.state.config['infra_external_ip'] = custom_ip
                    click.echo(f"✅ Using custom external IP: {custom_ip}")
                else:
                    click.echo("⚠️  No external IP provided. Traefik may not work correctly.")
                    infra_config['external_ip'] = ""
                    self.state.config['infra_external_ip'] = ""
        else:
            infra_config['external_ip'] = self.state.config['infra_external_ip']
        
        # Whitelisted IPs for Traefik
        if 'infra_whitelisted_ips' not in self.state.config:
            if 'gcp_whitelisted_ips' in self.state.config and self.state.config['gcp_whitelisted_ips']:
                # Handle gcp_whitelisted_ips - it should already be a list from GCP configuration
                if isinstance(self.state.config['gcp_whitelisted_ips'], list):
                    default_whitelisted_ips = self.state.config['gcp_whitelisted_ips']
                else:
                    # Fallback: parse as string if it's not a list (strict format, no quotes)
                    default_whitelisted_ips = [ip.strip() for ip in str(self.state.config['gcp_whitelisted_ips']).split(',') if ip.strip()]
                
                # Convert single IP to CIDR format if needed
                if len(default_whitelisted_ips) == 1 and '/' not in default_whitelisted_ips[0]:
                    default_whitelisted_ips = [f"{default_whitelisted_ips[0]}/32"]
                
                click.echo(f"✅ Using whitelisted IPs from infrastructure: {', '.join(default_whitelisted_ips)}")
                infra_config['whitelisted_environment_ips'] = default_whitelisted_ips
                self.state.config['infra_whitelisted_ips'] = default_whitelisted_ips
            else:
                # If gcp_whitelisted_ips is empty or not set, use default
                click.echo("ℹ️ No whitelisted IPs found from infrastructure, using default: 0.0.0.0/0")
                whitelisted_ips_input = safe_input(
                    "Enter whitelisted IP addresses for Traefik (comma-separated, no quotes): 192.168.1.1/32,10.0.0.1/32",
                    default="0.0.0.0/0"
                )
                # Parse comma-separated IPs into a list (strict format, no quotes)
                whitelisted_ips_list = [ip.strip() for ip in whitelisted_ips_input.split(',') if ip.strip()]
                infra_config['whitelisted_environment_ips'] = whitelisted_ips_list
                self.state.config['infra_whitelisted_ips'] = whitelisted_ips_list
        else:
            # Handle existing configuration - ensure it's a list
            existing_ips = self.state.config['infra_whitelisted_ips']
            if isinstance(existing_ips, str):
                # Parse comma-separated string into list (strict format, no quotes)
                infra_config['whitelisted_environment_ips'] = [ip.strip() for ip in existing_ips.split(',') if ip.strip()]
            else:
                infra_config['whitelisted_environment_ips'] = existing_ips
        
        # External DNS domain filters
        if 'infra_external_dns_domain_filters' not in self.state.config:
            infra_config['external_dns_domain_filters'] = safe_input(
                "Enter external DNS domain filters:",
                default=self.state.config['domain_name']
            )
            self.state.config['infra_external_dns_domain_filters'] = infra_config['external_dns_domain_filters']
        else:
            infra_config['external_dns_domain_filters'] = self.state.config['infra_external_dns_domain_filters']
        
        # Display final configuration
        click.echo("\n📋 Final Infrastructure Services Configuration:")
        click.echo(f"  Customer: {self.state.config['customer']}")
        click.echo(f"  Domain: {self.state.config['domain_name']}")
        click.echo(f"  Cloud Provider: {self.state.config['cloud_provider']}")
        click.echo(f"  Project ID: {infra_config['project_id']}")
        click.echo(f"  Region: {self.state.config['project_region']}")
        click.echo(f"  Kubeconfig: {self.state.kubeconfig_path or 'Not configured'}")
        click.echo(f"  External IP: {infra_config['external_ip']}")
        # Display whitelisted IPs properly (handle both lists and strings)
        if isinstance(infra_config['whitelisted_environment_ips'], list):
            click.echo(f"  Whitelisted IPs: {', '.join(infra_config['whitelisted_environment_ips'])}")
        else:
            click.echo(f"  Whitelisted IPs: {infra_config['whitelisted_environment_ips']}")
        click.echo(f"  External DNS Domain Filters: {infra_config['external_dns_domain_filters']}")
        
        # Confirm deployment
        if safe_select("Proceed with infrastructure services deployment?", ['Yes', 'No']) == 'No':
            click.echo("❌ Infrastructure services deployment cancelled")
            return {}
        
        return infra_config

    def _prepare_service_parameters(self, service_file: str, service_config: dict, infra_config: dict) -> dict:
        """Prepare parameters for a specific service based on its configuration"""
        params = {
            'metadata_collector': self._get_metadata_collector(),
            'cluster_name': f"fast-bi-{self.state.config['customer']}-platform",
            'kube_config_path': self.state.kubeconfig_path
        }
        
        # Add project_id and region only for services that require them
        if 'project_id' in service_config.get('required_params', []):
            if 'gcp_project_id' in self.state.config:
                params['project_id'] = self.state.config['gcp_project_id']
            else:
                params['project_id'] = f"fast-bi-{self.state.config['customer']}"
                
        if 'region' in service_config.get('required_params', []):
            if 'project_region' in self.state.config:
                params['region'] = self.state.config['project_region']
        
        # Add method parameter only for services that require it
        if 'method' in service_config.get('required_params', []):
            params['method'] = "local_vault"
        
        # Handle chart versions based on service type
        if service_file == "1.0_secret_operator":
            # Secret operator has different chart versions based on method
            if params['method'] == "local_vault":
                chart_config = service_config['chart_versions']['local_vault']
                params['chart_version'] = chart_config['chart_version']
                params['hc_vault_chart_version'] = chart_config['hc_vault_chart_version']
            else:
                chart_config = service_config['chart_versions']['external_infisical']
                params['chart_version'] = chart_config['chart_version']
        else:
            # Other services have single chart version
            params['chart_version'] = service_config['chart_version']
            
            # Add common parameters for non-secret-operator services
            if 'domain_name' in service_config.get('required_params', []):
                params['domain_name'] = self.state.config['domain_name']
            
            if 'user_email' in service_config.get('required_params', []):
                params['user_email'] = self.state.config['user_email']
            
            if 'cloud_provider' in service_config.get('required_params', []):
                params['cloud_provider'] = self.state.config['cloud_provider']
            
            if 'namespace' in service_config:
                params['namespace'] = service_config['namespace']
            
            # Add service-specific parameters
            if service_file == "3.0_external_dns":
                params['external_dns_domain_filters'] = infra_config.get('external_dns_domain_filters', self.state.config['domain_name'])
            
            if service_file == "4.0_traefik_lb":
                params['external_ip'] = infra_config.get('external_ip', "0.0.0.0")
                # Ensure whitelisted_environment_ips is a list
                whitelisted_ips = infra_config.get('whitelisted_environment_ips', "0.0.0.0/0")
                if isinstance(whitelisted_ips, str):
                    params['whitelisted_environment_ips'] = [whitelisted_ips]
                else:
                    params['whitelisted_environment_ips'] = whitelisted_ips
        
        # Handle skip_metadata by creating a dummy metadata collector
        if params.get('skip_metadata', True):
            class DummyMetadataCollector:
                def add_deployment_record(self, record):
                    click.echo(f"📝 Metadata collection skipped: {record}")
            
            params['metadata_collector'] = DummyMetadataCollector()
        
        # Remove skip_metadata from params as it's not a constructor parameter
        params.pop('skip_metadata', None)
        
        return params

    def _get_metadata_collector(self):
        """Get metadata collector instance"""
        class SimpleMetadataCollector:
            def __init__(self):
                self.deployment_records = []
            
            def add_deployment_record(self, record):
                click.echo(f"📝 Deployment record: {record}")
        
        return SimpleMetadataCollector()

    def _detect_kubeconfig_path(self) -> str:
        """Automatically detect kubeconfig path based on cloud provider"""
        cloud_provider = self.state.config.get('cloud_provider', 'gcp')
        customer = self.state.config.get('customer', '')
        
        # Define kubeconfig paths for different cloud providers
        kubeconfig_paths = {
            'gcp': f"terraform/google_cloud/terragrunt/bi-platform/17-kubeconfig/kubeconfig",
            'aws': f"terraform/aws_cloud/terragrunt/bi-platform/kubeconfig/kubeconfig",
            'azure': f"terraform/azure_cloud/terragrunt/bi-platform/kubeconfig/kubeconfig",
            'onprem': None  # On-premise requires user to provide path
        }
        
        default_path = kubeconfig_paths.get(cloud_provider)
        
        if default_path and Path(default_path).exists():
            click.echo(f"✅ Kubeconfig automatically detected: {default_path}")
            return default_path
        elif cloud_provider == 'onprem':
            click.echo("🔗 On-premise infrastructure detected - kubeconfig path required")
            return None
        else:
            click.echo(f"⚠️ Kubeconfig not found at expected location: {default_path}")
            return None

    def _collect_kubeconfig_path(self) -> bool:
        """Collect kubeconfig path from user or auto-detect"""
        click.echo("\n🔗 Kubeconfig Configuration")
        
        # Try to auto-detect kubeconfig path
        detected_path = self._detect_kubeconfig_path()
        
        if detected_path:
            # Auto-detected path exists, ask user if they want to use it or provide custom
            choice = safe_select(
                "Kubeconfig path detected. What would you like to do?",
                [
                    f"Use detected path: {detected_path}",
                    "Provide custom kubeconfig path"
                ]
            )
            
            if choice.startswith("Use detected path"):
                kubeconfig_path = detected_path
            else:
                kubeconfig_path = safe_input(
                    "Enter path to kubeconfig file",
                    validate=lambda path: Path(path).exists()
                )
        else:
            # No auto-detected path, ask user to provide one
            kubeconfig_path = safe_input(
                "Enter path to kubeconfig file",
                validate=lambda path: Path(path).exists()
            )
        
        if not kubeconfig_path:
            click.echo("❌ No kubeconfig file provided")
            return False
        
        # Verify kubeconfig is valid
        try:
            result = subprocess.run(
                ["kubectl", "--kubeconfig", kubeconfig_path, "cluster-info"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                click.echo("✅ Kubeconfig is valid and cluster is accessible")
                self.state.kubeconfig_path = kubeconfig_path
                self.state.save_state()
                return True
            else:
                click.echo(f"❌ Invalid kubeconfig: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            click.echo("❌ Timeout connecting to cluster")
            return False
        except Exception as e:
            click.echo(f"❌ Error validating kubeconfig: {str(e)}")
            return False

    def _use_existing_infrastructure(self) -> bool:
        """Use existing infrastructure with provided kubeconfig"""
        click.echo("🔗 Using existing infrastructure...")
        
        # Use the new kubeconfig collection method
        if self._collect_kubeconfig_path():
            self.state.infrastructure_deployed = True
            self.state.save_state()
            return True
        else:
            return False

    def phase_2_secrets(self) -> bool:
        """Phase 2: Generate Platform Secrets"""
        click.echo("\n🔐 PHASE 2: Generate Platform Secrets")
        
        if self.state.secrets_generated:
            click.echo("✅ Secrets already generated")
            return True

        # Check if we have the required configuration
        if not self.state.config:
            click.echo("❌ No configuration found. Please run Phase 1 first.")
            return False

        # Collect additional parameters needed for secrets generation
        secrets_config = self._collect_secrets_parameters()
        
        try:
            # Create CustomerSecretManager instance
            secret_manager = CustomerSecretManager(
                user_email=self.state.config['user_email'],
                method=secrets_config['vault_method'],
                customer=self.state.config['customer'],
                domain_name=self.state.config['domain_name'],
                data_analysis_platform=secrets_config['data_analysis_platform'],
                data_warehouse_platform=secrets_config['data_warehouse_platform'],
                bigquery_project_id=secrets_config['bigquery_project_id'],
                bigquery_region=secrets_config['bigquery_region'],
                data_platform_sa_json=secrets_config['data_platform_sa_json'],
                data_analysis_sa_json=secrets_config['data_analysis_sa_json'],
                project_id=secrets_config['project_id'],
                project_region=self.state.config['project_region'],
                git_provider=secrets_config['git_provider'],
                dag_repo_url=secrets_config['dag_repo_url'],
                data_repo_url=secrets_config['data_repo_url'],
                data_repo_main_branch=secrets_config['data_repo_main_branch'],
                repo_access_method=secrets_config['repo_access_method'],
                cloud_provider=self.state.config['cloud_provider'],
                git_provider_access_token=secrets_config['git_provider_access_token'],
                smtp_host=secrets_config.get('smtp_host'),
                smtp_port=secrets_config.get('smtp_port'),
                smtp_username=secrets_config.get('smtp_username'),
                smtp_password=secrets_config.get('smtp_password'),
                orchestrator_platform=secrets_config.get('orchestrator_platform', 'Airflow')
            )
            
            # Execute secrets generation
            click.echo("🚀 Generating platform secrets...")
            result = secret_manager.run()
            
            if result.get('status') == 'success':
                click.echo("✅ Platform secrets generated successfully")
                for message in result.get('messages', []):
                    click.echo(f"  - {message}")
                
                # If using deploy keys, read and display public keys for repository configuration
                if secrets_config.get('repo_access_method') == 'deploy_keys' and secrets_config.get('vault_method') == 'local_vault':
                    self._display_deploy_keys_for_repositories()
                
                self.state.secrets_generated = True
                self.state.save_state()
                return True
            else:
                click.echo(f"❌ Secrets generation failed: {result.get('error', 'Unknown error occurred')}")
                return False

        except Exception as e:
            click.echo(f"❌ Error generating secrets: {str(e)}")
            return False

    def phase_3_repositories(self) -> bool:
        """Phase 3: Configure Data Platform Repositories"""
        click.echo("\n📚 PHASE 3: Configure Data Platform Repositories")
        
        if self.state.repositories_configured:
            click.echo("✅ Repositories already configured")
            return True

        # Check if we have the required configuration
        if not self.state.config:
            click.echo("❌ No configuration found. Please run Phase 1 first.")
            return False

        if not self.state.secrets_generated:
            click.echo("❌ Secrets not generated. Please run Phase 2 first.")
            return False

        # Check if deploy keys were configured (if using deploy keys method)
        if self.state.config.get('secrets_repo_access_method') == 'deploy_keys':
            if not self._verify_deploy_keys_configured():
                click.echo("❌ Deploy keys not configured in repositories. Please add the deploy keys shown in Phase 2 to your repositories.")
                return False

        # Check DNS nameserver configuration for custom domains
        if not self._verify_dns_nameserver_configuration():
            click.echo("❌ DNS nameserver configuration required. Please configure the nameserver records as shown above.")
            return False

        # Collect repository configuration parameters
        repo_config = self._collect_repository_parameters()
        
        # Check if user cancelled the configuration
        if not repo_config:
            click.echo("❌ Repository configuration cancelled by user")
            return False
        
        try:
            # Import the repository configuration script
            from utils.customer_data_platform_repository_operator import CustomerDataPlatformRepositoryOperator
            
            # Create repository operator instance
            repo_operator = CustomerDataPlatformRepositoryOperator(
                customer=self.state.config['customer'],
                domain=self.state.config['domain_name'],
                method='local_vault',
                git_provider=repo_config['git_provider'],
                repo_authentication=repo_config['repo_access_method'],
                data_orchestrator_repo_url=repo_config['dag_repo_url'],
                data_model_repo_url=repo_config['data_repo_url'],
                global_access_token=repo_config.get('git_provider_access_token')
            )
            
            # Execute repository configuration
            click.echo("🚀 Configuring data platform repositories...")
            result = repo_operator.run()
            
            if result.get('status') == 'success':
                click.echo("✅ Data platform repositories configured successfully")
                for message in result.get('messages', []):
                    click.echo(f"  - {message}")
                
                self.state.repositories_configured = True
                self.state.save_state()
                return True
            else:
                click.echo(f"❌ Repository configuration failed: {result.get('error', 'Unknown error occurred')}")
                return False

        except Exception as e:
            click.echo(f"❌ Error configuring repositories: {str(e)}")
            return False

    def phase_4_infra_services(self) -> bool:
        """Phase 4: Deploy Infrastructure Services"""
        click.echo("\n🔧 PHASE 4: Deploy Infrastructure Services")
        
        if self.state.infra_services_deployed:
            click.echo("✅ Infrastructure services already deployed")
            return True

        # Check if we have the required configuration
        if not self.state.config:
            click.echo("❌ No configuration found. Please run Phase 1 first.")
            return False

        # Handle case where infrastructure is not deployed but user wants to use existing infrastructure
        if not self.state.infrastructure_deployed:
            click.echo("⚠️  Infrastructure not deployed in this session.")
            if not self.non_interactive:
                use_existing = safe_select(
                    "Do you want to use existing infrastructure?",
                    ["Yes, provide kubeconfig", "No, run Phase 1 first"]
                )
                if use_existing == "Yes, provide kubeconfig":
                    if self._use_existing_infrastructure():
                        click.echo("✅ Using existing infrastructure")
                    else:
                        click.echo("❌ Failed to configure existing infrastructure")
                        return False
                else:
                    click.echo("❌ Please run Phase 1 first to deploy infrastructure.")
                    return False
            else:
                click.echo("❌ Infrastructure not deployed. Please run Phase 1 first.")
                return False

        if not self.state.secrets_generated:
            click.echo("❌ Secrets not generated. Please run Phase 2 first.")
            return False

        if not self.state.repositories_configured:
            click.echo("❌ Repositories not configured. Please run Phase 3 first.")
            return False

        # Check if kubeconfig is available
        if not self.state.kubeconfig_path or not Path(self.state.kubeconfig_path).exists():
            click.echo("⚠️ Kubeconfig not found. Attempting to detect or collect kubeconfig path...")
            if not self._collect_kubeconfig_path():
                click.echo("❌ Kubeconfig configuration failed. Please ensure Phase 1 completed successfully or provide a valid kubeconfig path.")
                return False

        # Collect infrastructure services configuration
        infra_config = self._collect_infrastructure_services_parameters()
        
        # Check if user cancelled the deployment
        if not infra_config:
            click.echo("❌ Infrastructure services deployment cancelled by user")
            return False
        
        try:
            # Set KUBECONFIG environment variable
            os.environ['KUBECONFIG'] = self.state.kubeconfig_path
            
            # Load infrastructure services configuration
            config_path = "cli/config/infrastructure_services_config.json"
            if not Path(config_path).exists():
                click.echo(f"❌ Infrastructure services configuration not found: {config_path}")
                return False
            
            with open(config_path, 'r') as f:
                services_config = json.load(f)['infrastructure_services']
            
            # Deploy infrastructure services in order
            services_to_deploy = [
                ("Secret Operator", "1.0_secret_operator"),
                ("Cert Manager", "2.0_cert_manager"),
                ("External DNS", "3.0_external_dns"),
                ("Traefik Load Balancer", "4.0_traefik_lb"),
                ("StackGres PostgreSQL", "5.0_stackgres_postgresql"),
                ("Log Collector", "6.0_log_collector"),
                ("Services Monitoring", "7.0_services_monitoring"),
                ("Cluster Cleaner", "8.0_cluster_cleaner"),
                ("IDP SSO Manager", "9.0_idp_sso_manager"),
                ("Cluster PVC Autoscaler", "10.0_cluster_pvc_autoscaller")
            ]
            
            click.echo("🚀 Deploying infrastructure services...")
            
            # Show current deployment status
            deployed_services = []
            pending_services = []
            for service_name, service_file in services_to_deploy:
                if self.state.is_service_deployed("infrastructure_services", service_file):
                    deployed_services.append(service_name)
                else:
                    pending_services.append(service_name)
            
            if deployed_services:
                click.echo(f"✅ Already deployed: {', '.join(deployed_services)}")
            if pending_services:
                click.echo(f"⏳ Pending deployment: {', '.join(pending_services)}")
            click.echo("")
            
            deployed_count = 0
            total_services = len(services_to_deploy)
            
            for service_name, service_file in services_to_deploy:
                # Check if service is already deployed
                if self.state.is_service_deployed("infrastructure_services", service_file):
                    click.echo(f"⏭️  Skipping {service_name} (already deployed)")
                    deployed_count += 1
                    continue
                
                click.echo(f"🔧 Deploying {service_name}...")
                
                # Get service configuration
                if service_file not in services_config:
                    click.echo(f"⚠️ Configuration not found for {service_name}")
                    continue
                
                service_config = services_config[service_file]
                
                # Import the service module dynamically using importlib
                import importlib.util
                import sys
                
                # Construct the full path to the service file
                service_path = f"deployers/services/infra_services/{service_file}.py"
                
                if not Path(service_path).exists():
                    click.echo(f"❌ Service file not found: {service_path}")
                    continue
                
                # Load the module
                spec = importlib.util.spec_from_file_location(service_file, service_path)
                service_module = importlib.util.module_from_spec(spec)
                sys.modules[service_file] = service_module
                spec.loader.exec_module(service_module)
                
                # Get the service class (assuming it's the only class in the module)
                service_class = None
                
                # Define expected class names for each service
                expected_class_names = {
                    "1.0_secret_operator": "SecretManager",
                    "2.0_cert_manager": "CertManager", 
                    "3.0_external_dns": "ExternalDNS",
                    "4.0_traefik_lb": "TraefikIngress",
                    "5.0_stackgres_postgresql": "StackgresPostgresqlDeployer",
                    "6.0_log_collector": "PlatformLogCollector",
                    "7.0_services_monitoring": "PlatformMonitoring",
                    "8.0_cluster_cleaner": "Platformk8sCleaner",
                    "9.0_idp_sso_manager": "IdpSsoManager",
                    "10.0_cluster_pvc_autoscaller": "Platformk8sPvcAutoscaler"
                }
                
                expected_class_name = expected_class_names.get(service_file)
                
                for attr_name in dir(service_module):
                    attr = getattr(service_module, attr_name)
                    if isinstance(attr, type) and attr_name != 'MetadataCollector':
                        # Look for the expected class name first
                        if expected_class_name and attr_name == expected_class_name:
                            service_class = attr
                            break
                        # If no expected class name or not found, take the first class that's not a built-in or imported
                        elif not expected_class_name and not attr_name.startswith('_') and attr_name not in ['Environment', 'BaseLoader', 'Extension']:
                            service_class = attr
                            break
                
                if not service_class:
                    click.echo(f"❌ Service class not found in {service_file}")
                    continue
                
                # Prepare service parameters
                params = self._prepare_service_parameters(service_file, service_config, infra_config)
                
                # Create metadata collector
                metadata_collector = self._get_metadata_collector()
                
                # Create and deploy the service
                if service_file == "1.0_secret_operator":
                    # SecretManager expects: chart_version, customer, metadata_collector as positional arguments
                    # followed by optional keyword arguments
                    service_instance = service_class(
                        params['chart_version'],  # positional
                        self.state.config['customer'],  # positional
                        metadata_collector,  # positional - pass the actual metadata_collector object
                        kube_config_path=params.get('kube_config_path'),  # keyword
                        hc_vault_chart_version=params.get('hc_vault_chart_version'),
                        namespace=params.get('namespace', 'vault'),
                        method=params.get('method', 'local_vault')
                    )
                else:
                    # Other services can use keyword arguments
                    # Add customer parameter for services that need it
                    if 'customer' not in params:
                        params['customer'] = self.state.config['customer']
                    service_instance = service_class(**params)
                
                service_instance.metadata_collector = metadata_collector
                
                try:
                    deployment_result = service_instance.run()
                    
                    if deployment_result:
                        click.echo(f"✅ {service_name} deployed successfully")
                        deployed_count += 1
                        
                        # Mark service as deployed
                        self.state.mark_service_deployed("infrastructure_services", service_file, {
                            'deployment_result': str(deployment_result),
                            'deployed_at': datetime.now().isoformat()
                        })
                        
                    else:
                        click.echo(f"❌ {service_name} deployment failed")
                        
                except Exception as e:
                    click.echo(f"❌ Error deploying {service_name}: {str(e)}")
                    continue
            
            # Update overall phase status
            if deployed_count > 0 or all(self.state.is_service_deployed("infrastructure_services", service_file) for _, service_file in services_to_deploy):
                self.state.infra_services_deployed = True
                self.state.save_state()
                
                # Count how many services are actually deployed
                deployed_services_count = sum(1 for _, service_file in services_to_deploy if self.state.is_service_deployed("infrastructure_services", service_file))
                click.echo(f"\n✅ Phase 4 completed: {deployed_services_count}/{total_services} services deployed")
                
                # Display Keycloak configuration information
                self._display_keycloak_configuration_info()
                
                return True
            else:
                click.echo("❌ No infrastructure services were deployed successfully")
                return False
                
        except Exception as e:
            click.echo(f"❌ Error during infrastructure services deployment: {str(e)}")
            return False

    def _extract_keycloak_credentials(self, deployment_result: str) -> dict:
        """Extract Keycloak credentials from deployment result"""
        try:
            # Parse the deployment result string
            import ast
            result_dict = ast.literal_eval(deployment_result)
            
            if 'credentials' in result_dict:
                return result_dict['credentials']
            else:
                return {}
        except:
            return {}
    
    def _display_keycloak_configuration_info(self):
        """Display Keycloak configuration information for user setup"""
        # Check if IDP SSO Manager was deployed
        idp_service = self.state.deployed_services.get("infrastructure_services", {}).get("9.0_idp_sso_manager")
        
        if not idp_service or not idp_service.get('deployed'):
            return
        
        click.echo("\n🔐 KEYCLOAK CONFIGURATION INFORMATION")
        click.echo("=" * 60)
        
        # Extract credentials
        deployment_result = idp_service.get('deployment_info', {}).get('deployment_result', '')
        credentials = self._extract_keycloak_credentials(deployment_result)
        
        # Construct Keycloak admin console URL
        customer = self.state.config.get('customer', 'unknown')
        domain = self.state.config.get('domain_name', 'unknown')
        keycloak_url = f"https://login.{customer}.{domain}"
        
        if credentials:
            click.echo("🌐 Keycloak Admin Console:")
            click.echo(f"  URL: {keycloak_url}")
            click.echo("")
            click.echo("📋 Keycloak Admin Credentials:")
            click.echo(f"  Username: {credentials.get('username', 'Not available')}")
            click.echo(f"  Password: {credentials.get('password', 'Not available')}")
            click.echo("")
        
        # Show realm file information
        realm_file_path = f"charts/infra_services_charts/idp_sso_manager/{customer}_realm.json"
        
        click.echo("📁 Keycloak Realm Configuration:")
        click.echo(f"  Realm File: {realm_file_path}")
        click.echo(f"  Customer: {customer}")
        click.echo("")
        
        click.echo("🔧 Next Steps:")
        click.echo(f"  1. Open your browser and navigate to: {keycloak_url}")
        click.echo("  2. Log in using the admin credentials above")
        click.echo("  3. Import the realm configuration from the realm file")
        click.echo("  4. Configure any additional settings as needed")
        click.echo("  5. Test the SSO integration")
        click.echo("")
        
        click.echo("⚠️  IMPORTANT: Keep these credentials secure!")
        click.echo("=" * 60)

    def _verify_keycloak_configuration(self) -> bool:
        """Verify that Keycloak SSO is properly configured"""
        click.echo("\n🔐 Keycloak SSO Configuration Verification")
        click.echo("=" * 50)
        
        # Check if IDP SSO Manager was deployed
        idp_service = self.state.deployed_services.get("infrastructure_services", {}).get("9.0_idp_sso_manager")
        
        if not idp_service or not idp_service.get('deployed'):
            click.echo("❌ IDP SSO Manager not deployed. Please complete Phase 4 first.")
            return False
        
        # Extract credentials
        deployment_result = idp_service.get('deployment_info', {}).get('deployment_result', '')
        credentials = self._extract_keycloak_credentials(deployment_result)
        
        if not credentials:
            click.echo("❌ Keycloak credentials not found. Please check IDP deployment.")
            return False
        
        # Display current configuration
        customer = self.state.config.get('customer', 'unknown')
        domain = self.state.config.get('domain_name', 'unknown')
        realm_file_path = f"charts/infra_services_charts/idp_sso_manager/{customer}_realm.json"
        keycloak_url = f"https://login.{customer}.{domain}"
        
        click.echo("📋 Current Keycloak Configuration:")
        click.echo(f"  Admin Console URL: {keycloak_url}")
        click.echo(f"  Username: {credentials.get('username', 'Not available')}")
        click.echo(f"  Password: {credentials.get('password', 'Not available')}")
        click.echo(f"  Realm File: {realm_file_path}")
        click.echo("")
        
        # Check if we should skip confirmations
        skip_confirmations = self.state.config.get('skip_confirmations', False)
        if skip_confirmations:
            click.echo("⚠️  Skipping confirmations as configured")
        else:
            click.echo("ℹ️  Confirmations will be shown for critical steps (e.g., Keycloak configuration)")
        
        # Ask user to confirm Keycloak configuration
        click.echo("🔧 Keycloak Configuration Steps:")
        click.echo("  1. Access Keycloak admin console")
        click.echo("  2. Import the realm configuration from the realm file")
        click.echo("  3. Configure any additional settings")
        click.echo("  4. Test the SSO integration")
        click.echo("")
        
        # Ask user if they have completed the configuration
        configuration_choice = safe_select(
            "Have you completed the Keycloak SSO configuration?",
            [
                "Yes, Keycloak is configured and ready",
                "No, I need to configure Keycloak first",
                "Skip this verification (not recommended)"
            ]
        )
        
        if configuration_choice == "Yes, Keycloak is configured and ready":
            click.echo("✅ Keycloak SSO configuration verified")
            return True
        elif configuration_choice == "No, I need to configure Keycloak first":
            click.echo("⚠️ Please configure Keycloak SSO before proceeding with data services.")
            click.echo("   You can use the credentials and realm file shown above.")
            click.echo("   Run 'python cli.py --show-config' to see all configuration details.")
            
            # Show detailed help
            self._show_keycloak_setup_help()
            return False
        else:  # Skip verification
            click.echo("⚠️ Skipping Keycloak verification (data services may not work correctly)")
            return True

    def phase_5_data_services(self) -> bool:
        """Phase 5: Deploy Data Services"""
        click.echo("\n📊 PHASE 5: Deploy Data Services")
        
        if self.state.data_services_deployed:
            click.echo("✅ Data services already deployed")
            return True

        # Check if we have the required configuration
        if not self.state.config:
            click.echo("❌ No configuration found. Please run Phase 1 first.")
            return False

        # Handle case where infrastructure is not deployed but user wants to use existing infrastructure
        if not self.state.infrastructure_deployed:
            click.echo("⚠️  Infrastructure not deployed in this session.")
            if not self.non_interactive:
                use_existing = safe_select(
                    "Do you want to use existing infrastructure?",
                    ["Yes, provide kubeconfig", "No, run Phase 1 first"]
                )
                if use_existing == "Yes, provide kubeconfig":
                    if self._use_existing_infrastructure():
                        click.echo("✅ Using existing infrastructure")
                    else:
                        click.echo("❌ Failed to configure existing infrastructure")
                        return False
                else:
                    click.echo("❌ Please run Phase 1 first to deploy infrastructure.")
                    return False
            else:
                click.echo("❌ Infrastructure not deployed. Please run Phase 1 first.")
                return False

        if not self.state.secrets_generated:
            click.echo("❌ Secrets not generated. Please run Phase 2 first.")
            return False

        if not self.state.repositories_configured:
            click.echo("❌ Repositories not configured. Please run Phase 3 first.")
            return False

        if not self.state.infra_services_deployed:
            click.echo("❌ Infrastructure services not deployed. Please run Phase 4 first.")
            return False

        # Check if kubeconfig is available
        if not self.state.kubeconfig_path or not Path(self.state.kubeconfig_path).exists():
            click.echo("⚠️ Kubeconfig not found. Attempting to detect or collect kubeconfig path...")
            if not self._collect_kubeconfig_path():
                click.echo("❌ Kubeconfig configuration failed. Please ensure Phase 1 completed successfully or provide a valid kubeconfig path.")
                return False

        # Check if Keycloak SSO is configured (prerequisite)
        if not self._verify_keycloak_configuration():
            click.echo("❌ Keycloak SSO is not configured. Please complete Keycloak configuration before deploying data services.")
            return False

        # Collect data services configuration
        data_config = self._collect_data_services_parameters()
        
        # Check if user cancelled the deployment
        if not data_config:
            click.echo("❌ Data services deployment cancelled by user")
            return False
        
        try:
            # Set KUBECONFIG environment variable
            os.environ['KUBECONFIG'] = self.state.kubeconfig_path
            
            # Load data services configuration
            config_path = "cli/config/data_services_config.json"
            if not Path(config_path).exists():
                click.echo(f"❌ Data services configuration not found: {config_path}")
                return False
            
            with open(config_path, 'r') as f:
                services_config = json.load(f)['data_services']
            
            # Deploy data services in order
            services_to_deploy = [
                ("CICD Workload Runner", "1.0_cicd_workload_runner"),
                ("Object Storage Operator", "2.0_object_storage_operator"),
                ("Argo Workflows", "3.0_data-cicd-workflows"),
                ("Data Replication", "4.0_data_replication"),
                ("Data Orchestration", "5.0_data_orchestration"),
                ("Data Modeling", "6.0_data_modeling"),
                ("DCDQ Metadata Collector", "7.0_data_dcdq_meta_collect"),
                ("Data Analysis", "8.0_data_analysis"),
                ("Data Governance", "9.0_data_governance"),
                ("Data Platform User Console", "10.0_user_console")
            ]
            
            click.echo("🚀 Deploying data services...")
            
            # Show current deployment status
            deployed_services = []
            pending_services = []
            for service_name, service_file in services_to_deploy:
                if self.state.is_service_deployed("data_services", service_file):
                    deployed_services.append(service_name)
                else:
                    pending_services.append(service_name)
            
            if deployed_services:
                click.echo(f"✅ Already deployed: {', '.join(deployed_services)}")
            if pending_services:
                click.echo(f"⏳ Pending deployment: {', '.join(pending_services)}")
            click.echo("")
            
            deployed_count = 0
            total_services = len(services_to_deploy)
            
            for service_name, service_file in services_to_deploy:
                # Check if service is already deployed
                if self.state.is_service_deployed("data_services", service_file):
                    click.echo(f"⏭️  Skipping {service_name} (already deployed)")
                    deployed_count += 1
                    continue
                
                click.echo(f"🔧 Deploying {service_name}...")
                
                # Get service configuration
                if service_file not in services_config:
                    click.echo(f"⚠️ Configuration not found for {service_name}")
                    continue
                
                service_config = services_config[service_file]
                
                # Import the service module dynamically using importlib
                import importlib.util
                import sys
                
                # Construct the full path to the service file
                service_path = f"deployers/services/data_services/{service_file}.py"
                
                if not Path(service_path).exists():
                    click.echo(f"❌ Service file not found: {service_path}")
                    continue
                
                # Load the module
                spec = importlib.util.spec_from_file_location(service_file, service_path)
                service_module = importlib.util.module_from_spec(spec)
                sys.modules[service_file] = service_module
                spec.loader.exec_module(service_module)
                
                # Get the service class (assuming it's the only class in the module)
                service_class = None
                
                # Define expected class names for each data service
                expected_class_names = {
                    "1.0_cicd_workload_runner": "Platformk8sGitRunner",
                    "2.0_object_storage_operator": "PlatformObjectStorage",
                    "3.0_data-cicd-workflows": "PlatformDataCicdWorkflows",
                    "4.0_data_replication": "PlatformDataReplication",
                    "5.0_data_orchestration": "PlatformDataOrchestration",
                    "6.0_data_modeling": "PlatformDataModeling",
                    "7.0_data_dcdq_meta_collect": "DataDCDQMetaCollectDeployer",
                    "8.0_data_analysis": "DataAnalysisDeployer",
                    "9.0_data_governance": "DataGovernanceDeployer",
                    "10.0_user_console": "PlatformUserConsole"
                }
                
                expected_class_name = expected_class_names.get(service_file)
                
                for attr_name in dir(service_module):
                    attr = getattr(service_module, attr_name)
                    if isinstance(attr, type) and attr_name != 'MetadataCollector':
                        # Look for the expected class name first
                        if expected_class_name and attr_name == expected_class_name:
                            service_class = attr
                            break
                        # If no expected class name or not found, take the first class that's not a built-in or imported
                        elif not expected_class_name and not attr_name.startswith('_') and attr_name not in ['Environment', 'BaseLoader', 'Extension']:
                            service_class = attr
                            break
                
                if not service_class:
                    click.echo(f"❌ Service class not found in {service_file}")
                    continue
                
                # Prepare service parameters
                params = self._prepare_data_service_parameters(service_file, service_config, data_config)
                
                # Create metadata collector
                metadata_collector = self._get_metadata_collector()
                
                # Create and deploy the service
                service_instance = service_class(**params)
                service_instance.metadata_collector = metadata_collector
                
                try:
                    deployment_result = service_instance.run()
                    
                    if deployment_result:
                        click.echo(f"✅ {service_name} deployed successfully")
                        deployed_count += 1
                        
                        # Mark service as deployed
                        self.state.mark_service_deployed("data_services", service_file, {
                            'deployment_result': str(deployment_result),
                            'deployed_at': datetime.now().isoformat()
                        })
                        
                    else:
                        click.echo(f"❌ {service_name} deployment failed")
                        
                except Exception as e:
                    click.echo(f"❌ Error deploying {service_name}: {str(e)}")
                    continue
            
            # Update overall phase status
            if deployed_count > 0 or all(self.state.is_service_deployed("data_services", service_file) for _, service_file in services_to_deploy):
                self.state.data_services_deployed = True
                self.state.save_state()
                
                # Count how many services are actually deployed
                deployed_services_count = sum(1 for _, service_file in services_to_deploy if self.state.is_service_deployed("data_services", service_file))
                click.echo(f"\n✅ Phase 5 completed: {deployed_services_count}/{total_services} services deployed")
                return True
            else:
                click.echo("❌ No data services were deployed successfully")
                return False
                
        except Exception as e:
            click.echo(f"❌ Error during data services deployment: {str(e)}")
            return False

    def _collect_finalization_parameters(self) -> Dict:
        """Collect parameters needed for deployment finalization"""
        finalization_config = {}
        
        click.echo("\n📁 Deployment Finalization Configuration")
        
        # Git provider - allow reuse or new selection
        if 'secrets_git_provider' in self.state.config:
            default_git_provider = self.state.config['secrets_git_provider']
            click.echo(f"Current Git provider: {default_git_provider}")
            
            git_provider_input = safe_input(
                f"Enter Git provider name (github/gitlab/bitbucket/fastbi) for deployment repository (press Enter for {default_git_provider}):",
                default=default_git_provider
            )
            
            # Validate that the input is a valid git provider name, not a URL
            valid_providers = ['github', 'gitlab', 'bitbucket', 'fastbi']
            if git_provider_input.strip() and git_provider_input not in valid_providers:
                if 'http' in git_provider_input or 'git@' in git_provider_input:
                    click.echo("❌ Error: You entered a repository URL. Please enter a git provider name (github/gitlab/bitbucket/fastbi).")
                    click.echo("The repository URL will be asked for in the next step.")
                    return {}
                else:
                    click.echo(f"❌ Error: Invalid git provider '{git_provider_input}'. Valid options: {', '.join(valid_providers)}")
                    return {}
            
            if git_provider_input.strip():
                finalization_config['git_provider'] = git_provider_input
                click.echo(f"✅ Using new Git provider: {finalization_config['git_provider']}")
            else:
                finalization_config['git_provider'] = default_git_provider
                click.echo(f"✅ Using existing Git provider: {finalization_config['git_provider']}")
        else:
            finalization_config['git_provider'] = safe_select(
                "Select Git provider for deployment repository:",
                ['github', 'gitlab', 'bitbucket', 'fastbi']
            )
        
        # Git access token - allow reuse or new token
        if 'secrets_git_provider_access_token' in self.state.config:
            default_access_token = self.state.config['secrets_git_provider_access_token']
            click.echo("Current Git access token: [configured]")
            
            access_token_input = safe_input(
                "Enter Git access token for deployment repository (press Enter to reuse existing):",
                default=""
            )
            
            if access_token_input.strip():
                finalization_config['git_access_token'] = access_token_input
                click.echo("✅ Using new Git access token")
            else:
                finalization_config['git_access_token'] = default_access_token
                click.echo("✅ Using existing Git access token from secrets configuration")
        else:
            finalization_config['git_access_token'] = safe_input(
                "Enter Git access token for deployment repository:",
                validate=lambda text: len(text) > 0
            )
        
        # Git repository URL (always ask for this as it's specific to deployment files)
        if 'finalization_git_repo_url' not in self.state.config:
            finalization_config['git_repo_url'] = safe_input(
                "Enter Git repository URL for deployment files:",
                validate=lambda text: len(text) > 0 and ('http' in text or 'git@' in text)
            )
            self.state.config['finalization_git_repo_url'] = finalization_config['git_repo_url']
        else:
            default_repo_url = self.state.config['finalization_git_repo_url']
            click.echo(f"Current repository URL: {default_repo_url}")
            
            repo_url_input = safe_input(
                "Enter Git repository URL for deployment files (press Enter to reuse existing):",
                default=default_repo_url
            )
            
            if repo_url_input.strip():
                finalization_config['git_repo_url'] = repo_url_input
                self.state.config['finalization_git_repo_url'] = repo_url_input
                click.echo("✅ Using new repository URL")
            else:
                finalization_config['git_repo_url'] = default_repo_url
                click.echo("✅ Using existing repository URL")
        
        # Use existing configuration
        finalization_config['customer'] = self.state.config['customer']
        finalization_config['method'] = 'local_vault'
        finalization_config['cloud_provider'] = self.state.config['cloud_provider']
        finalization_config['kube_config_path'] = self.state.kubeconfig_path
        
        # Map fastbi to gitlab for InfrastructureDeploymentOperator compatibility
        if finalization_config['git_provider'] == 'fastbi':
            finalization_config['git_provider'] = 'gitlab'
            click.echo("ℹ️  Mapping 'fastbi' to 'gitlab' for deployment finalization")
        
        # Display finalization configuration
        click.echo("\n📋 Finalization Configuration:")
        click.echo(f"  Customer: {finalization_config['customer']}")
        click.echo(f"  Method: {finalization_config['method']}")
        click.echo(f"  Cloud Provider: {finalization_config['cloud_provider']}")
        click.echo(f"  Git Provider: {finalization_config['git_provider']}")
        click.echo(f"  Repository URL: {finalization_config['git_repo_url']}")
        click.echo(f"  Access Token: {'✅ Configured' if finalization_config.get('git_access_token') else '❌ Not configured'}")
        click.echo(f"  Kubeconfig: {finalization_config['kube_config_path']}")
        
        # Confirm finalization
        if safe_select("Proceed with deployment finalization?", ['Yes', 'No']) == 'No':
            click.echo("❌ Deployment finalization cancelled")
            return {}
        
        return finalization_config

    def phase_6_finalize(self) -> bool:
        """Phase 6: Finalize Deployment"""
        click.echo("\n✨ PHASE 6: Finalize Deployment")
        
        if self.state.deployment_finalized:
            click.echo("✅ Deployment already finalized")
            return True

        # Check if we have the required configuration
        if not self.state.config:
            click.echo("❌ No configuration found. Please run Phase 1 first.")
            return False

        if not self.state.infrastructure_deployed:
            click.echo("❌ Infrastructure not deployed. Please run Phase 1 first.")
            return False

        if not self.state.secrets_generated:
            click.echo("❌ Secrets not generated. Please run Phase 2 first.")
            return False

        if not self.state.repositories_configured:
            click.echo("❌ Repositories not configured. Please run Phase 3 first.")
            return False

        if not self.state.infra_services_deployed:
            click.echo("❌ Infrastructure services not deployed. Please run Phase 4 first.")
            return False

        if not self.state.data_services_deployed:
            click.echo("❌ Data services not deployed. Please run Phase 5 first.")
            return False

        # Collect finalization parameters
        finalization_config = self._collect_finalization_parameters()
        
        if not finalization_config:
            return False
        
        try:
            # Import the infrastructure deployment operator
            from utils.infrastructure_deployment_operator import InfrastructureDeploymentOperator
            
            # Get terraform_state from configuration
            terraform_state = self.state.config.get('gcp_terraform_state', 'remote')
            
            # Create infrastructure deployment operator instance
            deployment_operator = InfrastructureDeploymentOperator(
                customer=finalization_config['customer'],
                method=finalization_config['method'],
                cloud_provider=finalization_config['cloud_provider'],
                terraform_state=terraform_state,
                git_provider=finalization_config['git_provider'],
                git_repo_url=finalization_config['git_repo_url'],
                kube_config_path=finalization_config['kube_config_path'],
                git_access_token=finalization_config['git_access_token']
            )
            
            # Execute deployment finalization
            click.echo("🚀 Finalizing deployment and saving files to repository...")
            result = deployment_operator.collect_and_store_infrastructure()
            
            if result.get('status') == 'success':
                click.echo("✅ Deployment finalized successfully")
                for message in result.get('messages', []):
                    click.echo(f"  - {message}")
                
                # Display final deployment summary
                click.echo("\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
                click.echo("=" * 60)
                click.echo(f"Customer: {self.state.config['customer']}")
                click.echo(f"Domain: {self.state.config['domain_name']}")
                click.echo(f"Cloud Provider: {self.state.config['cloud_provider']}")
                click.echo(f"Terraform State: {terraform_state}")
                click.echo(f"Repository: {finalization_config['git_repo_url']}")
                click.echo("")
                click.echo("📋 Deployed Services:")
                
                # Infrastructure services
                infra_services = self.state.deployed_services.get("infrastructure_services", {})
                if infra_services:
                    click.echo("  🔧 Infrastructure Services:")
                    for service_file, service_info in infra_services.items():
                        if service_info.get('deployed'):
                            service_name = service_info.get('deployment_info', {}).get('service_name', service_file)
                            click.echo(f"    ✅ {service_name}")
                
                # Data services
                data_services = self.state.deployed_services.get("data_services", {})
                if data_services:
                    click.echo("  📊 Data Services:")
                    for service_file, service_info in data_services.items():
                        if service_info.get('deployed'):
                            service_name = service_info.get('deployment_info', {}).get('service_name', service_file)
                            click.echo(f"    ✅ {service_name}")
                
                click.echo("")
                click.echo("🔗 Access Information:")
                click.echo(f"  - IDP Console: https://login.{self.state.config['customer']}.{self.state.config['domain_name']}")
                click.echo(f"  - Fast.BI Platform: https://{self.state.config['customer']}.{self.state.config['domain_name']}")
                click.echo("")
                click.echo("📁 Deployment files have been saved to the specified Git repository.")
                
                # Add encryption key information
                if hasattr(deployment_operator, 'encryption_key'):
                    click.echo("")
                    click.echo("🔐 ENCRYPTION KEY")
                    click.echo("=" * 40)
                    click.echo("⚠️  IMPORTANT: Save this encryption key securely!")
                    click.echo("   Deployment files in the repository are encrypted for security.")
                    click.echo("   You will need this key to decrypt the files later.")
                    click.echo("")
                    click.echo(f"Generated encryption key: {deployment_operator.encryption_key}")
                    click.echo("")
                    click.echo("💡 Tip: Store this key in a secure password manager or vault.")
                    click.echo("=" * 40)
                
                click.echo("=" * 60)
                
                self.state.deployment_finalized = True
                self.state.save_state()
                return True
            else:
                click.echo(f"❌ Deployment finalization failed: {result.get('error', 'Unknown error occurred')}")
                return False

        except Exception as e:
            click.echo(f"❌ Error finalizing deployment: {str(e)}")
            return False

    def run_phase(self, phase: int) -> bool:
        """Run a specific phase"""
        phases = {
            1: ("Infrastructure Deployment", self.phase_1_infrastructure),
            2: ("Generate Platform Secrets", self.phase_2_secrets),
            3: ("Configure Repositories", self.phase_3_repositories),
            4: ("Deploy Infrastructure Services", self.phase_4_infra_services),
            5: ("Deploy Data Services", self.phase_5_data_services),
            6: ("Finalize Deployment", self.phase_6_finalize)
        }
        
        if phase not in phases:
            click.echo(f"❌ Invalid phase number. Must be between 1 and {len(phases)}", err=True)
            return False
        
        phase_name, phase_func = phases[phase]
        click.echo(f"\n📍 Running Phase {phase}: {phase_name}...")
        
        if phase_func():
            click.echo(f"✅ Phase {phase} completed successfully: {phase_name}")
            return True
        else:
            click.echo(f"❌ Phase {phase} failed: {phase_name}", err=True)
            return False

    def run_all_phases(self) -> bool:
        """Run all phases in sequence"""
        click.echo("\n🚀 Starting complete deployment process...")
        
        for phase in range(1, 7):
            if not self.run_phase(phase):
                return False
        
        click.echo("\n✨ All phases completed successfully!")
        return True

    def show_deployment_status(self):
        """Show detailed deployment status including individual services"""
        click.echo("\n📋 Detailed Deployment Status:")
        click.echo(f"  Customer: {self.state.config.get('customer', 'Not set')}")
        click.echo(f"  Email: {self.state.config.get('user_email', 'Not set')}")
        click.echo(f"  Cloud Provider: {self.state.config.get('cloud_provider', 'Not set')}")
        click.echo(f"  Domain: {self.state.config.get('domain_name', 'Not set')}")
        click.echo(f"  Terraform State: {self.state.config.get('gcp_terraform_state', 'Not set')}")
        click.echo(f"  Infrastructure Deployed: {'✅' if self.state.infrastructure_deployed else '❌'}")
        click.echo(f"  Secrets Generated: {'✅' if self.state.secrets_generated else '❌'}")
        click.echo(f"  Repositories Configured: {'✅' if self.state.repositories_configured else '❌'}")
        click.echo(f"  Infra Services Deployed: {'✅' if self.state.infra_services_deployed else '❌'}")
        click.echo(f"  Data Services Deployed: {'✅' if self.state.data_services_deployed else '❌'}")
        click.echo(f"  Deployment Finalized: {'✅' if self.state.deployment_finalized else '❌'}")
        
        # Show individual infrastructure services status
        if self.state.deployed_services.get("infrastructure_services"):
            click.echo("\n🔧 Infrastructure Services Status:")
            services_to_check = [
                ("Secret Operator", "1.0_secret_operator"),
                ("Cert Manager", "2.0_cert_manager"),
                ("External DNS", "3.0_external_dns"),
                ("Traefik Load Balancer", "4.0_traefik_lb"),
                ("StackGres PostgreSQL", "5.0_stackgres_postgresql"),
                ("Log Collector", "6.0_log_collector"),
                ("Services Monitoring", "7.0_services_monitoring"),
                ("Cluster Cleaner", "8.0_cluster_cleaner"),
                ("IDP SSO Manager", "9.0_idp_sso_manager"),
                ("Cluster PVC Autoscaler", "10.0_cluster_pvc_autoscaller")
            ]
            
            for service_name, service_file in services_to_check:
                if self.state.is_service_deployed("infrastructure_services", service_file):
                    deployment_info = self.state.deployed_services["infrastructure_services"].get(service_file, {})
                    deployed_at = deployment_info.get('deployed_at', 'Unknown')
                    click.echo(f"    {service_name}: ✅ (deployed at {deployed_at})")
                else:
                    click.echo(f"    {service_name}: ❌")
        
        # Display Keycloak configuration information if available
        self._display_keycloak_configuration_info()

    def show_configuration_summary(self):
        """Show a comprehensive configuration summary for user setup"""
        click.echo("\n📋 DEPLOYMENT CONFIGURATION SUMMARY")
        click.echo("=" * 60)
        
        # Basic configuration
        click.echo("🔧 Basic Configuration:")
        click.echo(f"  Customer: {self.state.config.get('customer', 'Not set')}")
        click.echo(f"  Domain: {self.state.config.get('domain_name', 'Not set')}")
        click.echo(f"  Cloud Provider: {self.state.config.get('cloud_provider', 'Not set')}")
        click.echo(f"  Region: {self.state.config.get('project_region', 'Not set')}")
        click.echo(f"  Project ID: {self.state.config.get('gcp_project_id', 'Not set')}")
        click.echo(f"  Terraform State: {self.state.config.get('gcp_terraform_state', 'Not set')}")
        click.echo("")
        
        # Infrastructure information
        if self.state.infrastructure_deployed:
            click.echo("🏗️ Infrastructure Information:")
            click.echo(f"  Kubeconfig: {self.state.kubeconfig_path or 'Not configured'}")
            click.echo(f"  External IP: {self.state.config.get('infra_external_ip', 'Not set')}")
            # Display whitelisted IPs properly (handle both lists and strings)
            whitelisted_ips = self.state.config.get('infra_whitelisted_ips', 'Not set')
            if isinstance(whitelisted_ips, list):
                click.echo(f"  Whitelisted IPs: {', '.join(whitelisted_ips)}")
            else:
                click.echo(f"  Whitelisted IPs: {whitelisted_ips}")
            click.echo("")
        
        # Repository information
        if self.state.repositories_configured:
            click.echo("📚 Repository Configuration:")
            click.echo(f"  Git Provider: {self.state.config.get('secrets_git_provider', 'Not set')}")
            click.echo(f"  DAG Repository: {self.state.config.get('secrets_dag_repo_url', 'Not set')}")
            click.echo(f"  Data Repository: {self.state.config.get('secrets_data_repo_url', 'Not set')}")
            click.echo("")
        
        # Platform configuration
        click.echo("🎯 Platform Configuration:")
        click.echo(f"  Data Analysis Platform: {self.state.config.get('secrets_data_analysis_platform', 'Not set')}")
        click.echo(f"  Data Warehouse Platform: {self.state.config.get('secrets_data_warehouse_platform', 'Not set')}")
        click.echo(f"  Orchestrator Platform: {self.state.config.get('secrets_orchestrator_platform', 'Not set')}")
        click.echo("")
        
        # Display Keycloak configuration
        self._display_keycloak_configuration_info()
        
        click.echo("=" * 60)

    def _show_keycloak_setup_help(self):
        """Show detailed help for Keycloak setup"""
        click.echo("\n🔐 KEYCLOAK SETUP HELP")
        click.echo("=" * 50)
        
        # Extract credentials
        idp_service = self.state.deployed_services.get("infrastructure_services", {}).get("9.0_idp_sso_manager")
        if idp_service and idp_service.get('deployed'):
            deployment_result = idp_service.get('deployment_info', {}).get('deployment_result', '')
            credentials = self._extract_keycloak_credentials(deployment_result)
            
            if credentials:
                customer = self.state.config.get('customer', 'unknown')
                domain = self.state.config.get('domain_name', 'unknown')
                realm_file_path = f"charts/infra_services_charts/idp_sso_manager/{customer}_realm.json"
                
                click.echo("📋 Keycloak Access Information:")
                click.echo(f"  Admin Console URL: https://login.{customer}.{domain}")
                click.echo(f"  Username: {credentials.get('username', 'Not available')}")
                click.echo(f"  Password: {credentials.get('password', 'Not available')}")
                click.echo("")
                
                click.echo("📁 Realm Configuration:")
                click.echo(f"  Realm File: {realm_file_path}")
                click.echo(f"  File Size: {Path(realm_file_path).stat().st_size if Path(realm_file_path).exists() else 'Not found'} bytes")
                click.echo("")
                
                click.echo("🔧 Step-by-Step Configuration:")
                click.echo("  1. Open your browser and navigate to the Admin Console URL")
                click.echo("  2. Log in using the credentials above")
                click.echo("  3. Click 'Add realm' or 'Import'")
                click.echo("  4. Select the realm file from the path shown above")
                click.echo("  5. Review and confirm the realm import")
                click.echo("  6. Test the SSO integration with a sample application")
                click.echo("")
                
                click.echo("⚠️ Important Notes:")
                click.echo("  - Keep the credentials secure")
                click.echo("  - The realm file contains all client configurations")
                click.echo("  - Data services require SSO to be properly configured")
                click.echo("  - You can run 'python cli.py --show-config' anytime to see this information")
                click.echo("")
                
                click.echo("✅ Once you've completed the Keycloak setup, run Phase 5 again.")
        
        click.echo("=" * 50)

    def _collect_data_services_parameters(self) -> Dict:
        """Collect parameters needed for data services deployment"""
        data_config = {}
        
        click.echo("\n📊 Data Services Configuration")
        
        # Use project ID from infrastructure
        if 'gcp_project_id' in self.state.config:
            data_config['project_id'] = self.state.config['gcp_project_id']
        else:
            data_config['project_id'] = f"fast-bi-{self.state.config['customer']}"
        
        # Display current configuration
        click.echo("📋 Data Services Configuration:")
        click.echo(f"  Customer: {self.state.config['customer']}")
        click.echo(f"  Domain: {self.state.config['domain_name']}")
        click.echo(f"  Cloud Provider: {self.state.config['cloud_provider']}")
        click.echo(f"  Project ID: {data_config['project_id']}")
        click.echo(f"  Region: {self.state.config['project_region']}")
        click.echo(f"  Kubeconfig: {self.state.kubeconfig_path or 'Not configured'}")
        
        # Collect additional parameters for specific services
        click.echo("\n📋 Collecting additional parameters for data services...")
        
        # Git provider and token for CICD Workload Runner
        # Use existing values from secrets configuration if available
        if 'data_git_provider' not in self.state.config or not self.state.config['data_git_provider']:
            # Try to use from secrets configuration
            if 'secrets_git_provider' in self.state.config:
                data_config['git_provider'] = self.state.config['secrets_git_provider']
                self.state.config['data_git_provider'] = data_config['git_provider']
                click.echo(f"✅ Using Git provider from secrets: {data_config['git_provider']}")
            else:
                data_config['git_provider'] = safe_select(
                    "Select Git provider for CICD:",
                    ['github', 'gitlab', 'bitbucket', 'fastbi']
                )
                self.state.config['data_git_provider'] = data_config['git_provider']
        else:
            data_config['git_provider'] = self.state.config['data_git_provider']
        
        if 'data_git_runner_token' not in self.state.config:
            # Try to reuse from secrets configuration
            if 'secrets_git_provider_access_token' in self.state.config:
                default_runner_token = self.state.config['secrets_git_provider_access_token']
                click.echo(f"Current Git runner token: [configured]")
                
                runner_token_input = safe_input(
                    "Enter Git runner access token for CICD (press Enter to reuse from secrets):",
                    default=""
                )
                
                if runner_token_input.strip():
                    data_config['git_runner_access_token'] = runner_token_input
                    self.state.config['data_git_runner_token'] = runner_token_input
                    click.echo("✅ Using new Git runner token")
                else:
                    data_config['git_runner_access_token'] = default_runner_token
                    self.state.config['data_git_runner_token'] = default_runner_token
                    click.echo("✅ Using Git runner token from secrets configuration")
            else:
                data_config['git_runner_access_token'] = safe_input(
                    "Enter Git runner access token for CICD:",
                    validate=lambda text: len(text) > 0
                )
                self.state.config['data_git_runner_token'] = data_config['git_runner_access_token']
        else:
            data_config['git_runner_access_token'] = self.state.config['data_git_runner_token']
        
        # Data replication destination type
        if 'data_replication_destination_type' not in self.state.config or not self.state.config['data_replication_destination_type']:
            # Try to use from secrets configuration
            if 'secrets_data_warehouse_platform' in self.state.config:
                data_config['data_replication_default_destination_type'] = self.state.config['secrets_data_warehouse_platform']
                self.state.config['data_replication_destination_type'] = data_config['data_replication_default_destination_type']
                click.echo(f"✅ Using data replication destination from secrets: {data_config['data_replication_default_destination_type']}")
            else:
                data_config['data_replication_default_destination_type'] = safe_select(
                    "Select default data replication destination:",
                    ['bigquery', 'snowflake', 'redshift']
                )
                self.state.config['data_replication_destination_type'] = data_config['data_replication_default_destination_type']
        else:
            data_config['data_replication_default_destination_type'] = self.state.config['data_replication_destination_type']
        
        # BI system for data analysis
        if 'data_bi_system' not in self.state.config or not self.state.config['data_bi_system']:
            # Try to use from secrets configuration
            if 'secrets_data_analysis_platform' in self.state.config:
                data_config['bi_system'] = self.state.config['secrets_data_analysis_platform']
                self.state.config['data_bi_system'] = data_config['bi_system']
                click.echo(f"✅ Using BI system from secrets: {data_config['bi_system']}")
            else:
                data_config['bi_system'] = safe_select(
                    "Select BI system for data analysis:",
                    ['superset', 'lightdash', 'metabase', 'looker']
                )
                self.state.config['data_bi_system'] = data_config['bi_system']
        else:
            data_config['bi_system'] = self.state.config['data_bi_system']
        
        # Debug: Show what BI system value we have
        click.echo(f"🔍 Debug: BI system value = '{data_config.get('bi_system', 'NOT_SET')}'")
        click.echo(f"🔍 Debug: secrets_data_analysis_platform = '{self.state.config.get('secrets_data_analysis_platform', 'NOT_SET')}'")
        click.echo(f"🔍 Debug: data_bi_system = '{self.state.config.get('data_bi_system', 'NOT_SET')}'")
        
        # Data governance parameters - vault token
        if 'data_governance_vault_secrets' not in self.state.config or not self.state.config['data_governance_vault_secrets']:
            if self.non_interactive:
                # In non-interactive mode, automatically try to retrieve from Kubernetes
                click.echo("🤖 Non-interactive mode: Attempting to retrieve vault token from Kubernetes...")
                vault_token = self._get_vault_token_from_k8s()
                if vault_token:
                    data_config['vault_secrets'] = vault_token
                    self.state.config['data_governance_vault_secrets'] = vault_token
                    click.echo("✅ Vault token retrieved successfully from Kubernetes")
                else:
                    click.echo("⚠️ Failed to retrieve vault token from Kubernetes. Data Governance may not work correctly.")
                    data_config['vault_secrets'] = ""
            else:
                data_config['vault_secrets'] = self._collect_vault_token()
                self.state.config['data_governance_vault_secrets'] = data_config['vault_secrets']
        else:
            data_config['vault_secrets'] = self.state.config['data_governance_vault_secrets']
        
        # Image versions for user console
        if 'user_console_web_core_version' not in self.state.config:
            data_config['tsb_fastbi_web_core_image_version'] = safe_input(
                "Enter TSB FastBI web core image version:",
                default="v2.1.6"
            )
            self.state.config['user_console_web_core_version'] = data_config['tsb_fastbi_web_core_image_version']
        else:
            data_config['tsb_fastbi_web_core_image_version'] = self.state.config['user_console_web_core_version']
        
        if 'user_console_dbt_init_version' not in self.state.config:
            data_config['tsb_dbt_init_core_image_version'] = safe_input(
                "Enter TSB DBT init core image version:",
                default="v0.5.4"
            )
            self.state.config['user_console_dbt_init_version'] = data_config['tsb_dbt_init_core_image_version']
        else:
            data_config['tsb_dbt_init_core_image_version'] = self.state.config['user_console_dbt_init_version']
        
        # Display final configuration
        click.echo("\n📋 Final Data Services Configuration:")
        click.echo(f"  Customer: {self.state.config['customer']}")
        click.echo(f"  Domain: {self.state.config['domain_name']}")
        click.echo(f"  Cloud Provider: {self.state.config['cloud_provider']}")
        click.echo(f"  Project ID: {data_config['project_id']}")
        click.echo(f"  Region: {self.state.config['project_region']}")
        click.echo(f"  Kubeconfig: {self.state.kubeconfig_path or 'Not configured'}")
        click.echo(f"  Git Provider: {data_config['git_provider']}")
        click.echo(f"  Git Runner Token: {'✅ Configured' if data_config.get('git_runner_access_token') else '❌ Not configured'}")
        click.echo(f"  Data Replication Destination: {data_config['data_replication_default_destination_type']}")
        click.echo(f"  BI System: {data_config['bi_system']}")
        click.echo(f"  Vault Token: {'✅ Configured' if data_config.get('vault_secrets') else '❌ Not configured'}")
        click.echo(f"  Web Core Version: {data_config['tsb_fastbi_web_core_image_version']}")
        click.echo(f"  DBT Init Version: {data_config['tsb_dbt_init_core_image_version']}")
        
        # Confirm deployment
        if safe_select("Proceed with data services deployment?", ['Yes', 'No']) == 'No':
            click.echo("❌ Data services deployment cancelled")
            return {}
        
        return data_config

    def _prepare_data_service_parameters(self, service_file: str, service_config: dict, data_config: dict) -> dict:
        """Prepare parameters for a specific data service based on its configuration"""
        params = {
            'customer': self.state.config['customer'],
            'metadata_collector': self._get_metadata_collector(),
            'cluster_name': f"fast-bi-{self.state.config['customer']}-platform",
            'kube_config_path': self.state.kubeconfig_path,
            'method': "local_vault"
        }
        
        # Add project_id and region only for services that require them
        if 'project_id' in service_config.get('required_params', []):
            if 'gcp_project_id' in self.state.config:
                params['project_id'] = self.state.config['gcp_project_id']
            else:
                params['project_id'] = f"fast-bi-{self.state.config['customer']}"
                
        if 'region' in service_config.get('required_params', []):
            if 'project_region' in self.state.config:
                params['region'] = self.state.config['project_region']
        
        # Add common parameters
        if 'domain_name' in service_config.get('required_params', []):
            params['domain_name'] = self.state.config['domain_name']
        
        if 'cloud_provider' in service_config.get('required_params', []):
            params['cloud_provider'] = self.state.config['cloud_provider']
        
        if 'namespace' in service_config:
            params['namespace'] = service_config['namespace']
        
        # Add chart versions
        if 'chart_version' in service_config:
            params['chart_version'] = service_config['chart_version']
        
        if 'app_version' in service_config:
            params['app_version'] = service_config['app_version']
        
        if 'operator_chart_version' in service_config:
            params['operator_chart_version'] = service_config['operator_chart_version']
        
        # Add prerequest chart version for data governance
        if 'prerequest_chart_version' in service_config:
            params['prerequest_chart_version'] = service_config['prerequest_chart_version']
        
        # Add service-specific parameters
        if service_file == "1.0_cicd_workload_runner":
            params['git_provider'] = data_config.get('git_provider', 'github')
            params['git_runner_access_token'] = data_config.get('git_runner_access_token', '')
        
        if service_file == "4.0_data_replication":
            params['data_replication_default_destination_type'] = data_config.get('data_replication_default_destination_type', 'bigquery')
        
        if service_file == "8.0_data_analysis":
            params['bi_system'] = data_config.get('bi_system', 'superset')
        
        if service_file == "9.0_data_governance":
            params['eck_es_chart_version'] = service_config.get('eck_es_chart_version', "0.16.0")
            params['eck_es_app_version'] = service_config.get('eck_es_app_version', "8.17.0")
            params['eck_es_op_chart_version'] = service_config.get('eck_es_op_chart_version', "3.1.0")
            params['vault_secrets'] = data_config.get('vault_secrets', '')
            # Add prerequest chart version for data governance
            if 'prerequest_chart_version' in service_config:
                params['prerequest_chart_version'] = service_config['prerequest_chart_version']
        
        if service_file == "10.0_user_console":
            params['tsb_fastbi_web_core_image_version'] = data_config.get('tsb_fastbi_web_core_image_version', 'v2.1.6')
            params['tsb_dbt_init_core_image_version'] = data_config.get('tsb_dbt_init_core_image_version', 'v0.5.4')
        
        # Add app_version for services that need it
        if service_file in ["5.0_data_orchestration", "6.0_data_modeling", "7.0_data_dcdq_meta_collect", "8.0_data_analysis"]:
            if 'app_version' in service_config:
                params['app_version'] = service_config['app_version']
        
        # Remove skip_metadata from params as it's not a constructor parameter
        # It's handled by the metadata collector
        params.pop('skip_metadata', None)
        
        return params

    def _get_vault_token_from_k8s(self) -> str:
        """Get vault token from Kubernetes secret"""
        try:
            click.echo("🔍 Retrieving vault token from Kubernetes...")
            
            # Run kubectl command to get the vault token
            result = subprocess.run([
                "kubectl", "--kubeconfig", self.state.kubeconfig_path,
                "get", "secret", "vault-init", "-n", "vault",
                "-o", "jsonpath={.data.root-token}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                # Decode base64
                import base64
                vault_token = base64.b64decode(result.stdout.strip()).decode('utf-8')
                click.echo("✅ Vault token retrieved successfully from Kubernetes")
                return vault_token
            else:
                click.echo(f"❌ Failed to retrieve vault token: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            click.echo("❌ Timeout retrieving vault token")
            return ""
        except Exception as e:
            click.echo(f"❌ Error retrieving vault token: {str(e)}")
            return ""

    def _collect_vault_token(self) -> str:
        """Collect vault token from user or Kubernetes"""
        click.echo("\n🔐 Vault Token Configuration")
        click.echo("Data Governance requires a vault token for storing secrets.")
        
        choice = safe_select(
            "How would you like to provide the vault token?",
            [
                "Retrieve automatically from Kubernetes (recommended)",
                "Enter manually",
                "Skip for now (not recommended)"
            ]
        )
        
        if choice == "Retrieve automatically from Kubernetes (recommended)":
            vault_token = self._get_vault_token_from_k8s()
            if vault_token:
                return vault_token
            else:
                click.echo("⚠️ Automatic retrieval failed. Please enter manually.")
                return self._collect_vault_token_manual()
        elif choice == "Enter manually":
            return self._collect_vault_token_manual()
        else:
            click.echo("⚠️ Skipping vault token configuration. Data Governance may not work correctly.")
            return ""

    def _collect_vault_token_manual(self) -> str:
        """Collect vault token manually from user"""
        vault_token = safe_input(
            "Enter vault token (from vault-init secret in vault namespace):",
            validate=lambda text: len(text) > 0
        )
        return vault_token

def collect_basic_config(use_simple_input: bool = False) -> Dict:
    """Collect basic configuration that's needed across all phases"""
    config = {}
    
    click.echo("\n📝 Basic Configuration (needed for all phases)")
    
    if use_simple_input:
        config['customer'] = safe_input(
            "Enter customer tenant name",
            validate=lambda text: len(text) >= 1 and len(text) <= 64
        )
        
        config['user_email'] = safe_input(
            "Enter admin email",
            validate=lambda text: '@' in text and len(text) <= 64
        )
        
        config['cloud_provider'] = safe_select(
            "Select cloud provider",
            ['gcp', 'aws', 'azure', 'onprem']
        )
        
        # Don't ask for project ID here - it will be handled in the infrastructure phase
        # config['project_id'] = safe_input(
        #     "Enter project ID",
        #     default=f"fast-bi-{config['customer']}"
        # )
        
        # For on-premise, region might not be relevant, but we'll still collect it for consistency
        if config['cloud_provider'] == 'onprem':
            config['project_region'] = safe_input(
                "Enter deployment region/location (e.g., datacenter, office)",
                default="on-premises"
            )
        else:
            config['project_region'] = safe_input(
                "Enter project region",
                default="us-central1"
            )
        
        config['domain_name'] = safe_input(
            "Enter domain name (e.g., fast.bi)",
            validate=lambda text: len(text) > 0
        )
    else:
        config['customer'] = questionary.text(
            "Enter customer tenant name:",
            validate=lambda text: len(text) >= 1 and len(text) <= 64
        ).ask()

        config['user_email'] = questionary.text(
            "Enter admin email:",
            validate=lambda text: '@' in text and len(text) <= 64
        ).ask()

        config['cloud_provider'] = questionary.select(
            "Select cloud provider:",
            choices=['gcp', 'aws', 'azure', 'onprem']
        ).ask()

        # Don't ask for project ID here - it will be handled in the infrastructure phase
        # config['project_id'] = questionary.text(
        #     "Enter project ID:",
        #     default=f"fast-bi-{config['customer']}"
        # ).ask()

        # For on-premise, region might not be relevant, but we'll still collect it for consistency
        if config['cloud_provider'] == 'onprem':
            config['project_region'] = questionary.text(
                "Enter deployment region/location (e.g., datacenter, office):",
                default="on-premises"
            ).ask()
        else:
            config['project_region'] = questionary.text(
                "Enter project region:",
                default="us-central1"
            ).ask()

        config['domain_name'] = questionary.text(
            "Enter domain name (e.g., fast.bi):",
            validate=lambda text: len(text) > 0
        ).ask()

    return config

class EnvironmentDestroyer:
    """Handles destruction of the entire Fast.BI environment"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = DeploymentState()
        self.state.load_state(state_file)
    
    def destroy_environment(self):
        """Destroy the entire environment in the correct order"""
        click.echo("\n🗑️  ENVIRONMENT DESTRUCTION")
        click.echo("=" * 50)
        
        if not self.state.config:
            click.echo("❌ No deployment configuration found. Nothing to destroy.")
            return
        
        # Show what will be destroyed
        self._show_destruction_summary()
        
        # Step 1: Destroy Kubernetes resources (Helm charts and namespaces)
        self._destroy_kubernetes_resources()
        
        # Step 2: Destroy cloud infrastructure
        self._destroy_cloud_infrastructure()
        
        # Step 3: Clean up state and configuration
        self._cleanup_state()
        
        click.echo("\n✅ Environment destruction completed successfully!")
        click.echo("💡 You can now run 'python cli.py' to start a fresh deployment.")
    
    def _show_destruction_summary(self):
        """Show what will be destroyed"""
        click.echo("📋 Destruction Summary:")
        click.echo(f"  Customer: {self.state.config.get('customer', 'Unknown')}")
        click.echo(f"  Cloud Provider: {self.state.config.get('cloud_provider', 'Unknown')}")
        click.echo(f"  Domain: {self.state.config.get('domain_name', 'Unknown')}")
        
        # Count deployed services
        infra_services = len([s for s in self.state.deployed_services.get("infrastructure_services", {}).values() if s.get('deployed')])
        data_services = len([s for s in self.state.deployed_services.get("data_services", {}).values() if s.get('deployed')])
        
        click.echo(f"  Infrastructure Services: {infra_services} deployed")
        click.echo(f"  Data Services: {data_services} deployed")
        click.echo("")
    
    def _destroy_kubernetes_resources(self):
        """Destroy all Kubernetes resources (Helm charts and namespaces)"""
        click.echo("🔧 Step 1: Destroying Kubernetes resources...")
        
        # Get kubeconfig path
        kubeconfig_path = self.state.kubeconfig_path
        if not kubeconfig_path or not Path(kubeconfig_path).exists():
            click.echo("⚠️  Kubeconfig not found. Skipping Kubernetes resource destruction.")
            click.echo(f"  Expected path: {kubeconfig_path}")
            return
        
        # Set KUBECONFIG environment variable
        os.environ['KUBECONFIG'] = kubeconfig_path
        
        try:
            # Destroy data services first (reverse order of deployment)
            self._destroy_data_services()
            
            # Destroy infrastructure services
            self._destroy_infrastructure_services()
            
            # Delete custom namespaces
            self._delete_custom_namespaces()
            
            click.echo("✅ Kubernetes resources destroyed successfully")
            
        except Exception as e:
            click.echo(f"❌ Error destroying Kubernetes resources: {str(e)}")
            click.echo("⚠️  You may need to manually clean up Kubernetes resources")
    
    def _destroy_data_services(self):
        """Destroy all data services in reverse deployment order"""
        click.echo("  📊 Destroying data services...")
        
        # Data services in reverse deployment order
        data_services = [
            "10.0_user_console",
            "9.0_data_governance", 
            "8.0_data_analysis",
            "7.0_data_dcdq_meta_collect",
            "6.0_data_modeling",
            "5.0_data_orchestration",
            "4.0_data_replication",
            "3.0_data-cicd-workflows",
            "2.0_object_storage_operator",
            "1.0_cicd_workload_runner"
        ]
        
        for service in data_services:
            if self.state.is_service_deployed("data_services", service):
                click.echo(f"    🗑️  Destroying {service}...")
                self._destroy_helm_release(service)
    
    def _destroy_infrastructure_services(self):
        """Destroy all infrastructure services in reverse deployment order"""
        click.echo("  🏗️  Destroying infrastructure services...")
        
        # Infrastructure services in reverse deployment order
        infra_services = [
            "10.0_cluster_pvc_autoscaller",
            "9.0_idp_sso_manager",
            "8.0_cluster_cleaner",
            "7.0_services_monitoring",
            "6.0_log_collector",
            "5.0_stackgres_postgresql",
            "4.0_traefik_lb",
            "3.0_external_dns",
            "2.0_cert_manager",
            "1.0_secret_operator"
        ]
        
        for service in infra_services:
            if self.state.is_service_deployed("infrastructure_services", service):
                click.echo(f"    🗑️  Destroying {service}...")
                self._destroy_helm_release(service)
    
    def _destroy_helm_release(self, service_name: str):
        """Destroy a specific Helm release by fetching all releases from the cluster"""
        try:
            # Load service configurations to get namespace
            service_config = None
            namespace = "default"
            
            # Try to find service in infrastructure services config
            infra_config_path = "cli/config/infrastructure_services_config.json"
            if Path(infra_config_path).exists():
                with open(infra_config_path, 'r') as f:
                    infra_config = json.load(f)
                    if service_name in infra_config.get("infrastructure_services", {}):
                        service_config = infra_config["infrastructure_services"][service_name]
                        namespace = service_config.get("namespace", "default")
            
            # Try to find service in data services config
            if not service_config:
                data_config_path = "cli/config/data_services_config.json"
                if Path(data_config_path).exists():
                    with open(data_config_path, 'r') as f:
                        data_config = json.load(f)
                        if service_name in data_config.get("data_services", {}):
                            service_config = data_config["data_services"][service_name]
                            namespace = service_config.get("namespace", "default")
            
            # Fetch all Helm releases in the namespace
            result = subprocess.run(
                ['helm', 'list', '--namespace', namespace, '--output', 'json'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                click.echo(f"      ⚠️  No Helm releases found in namespace {namespace}")
                return
            
            # Parse the Helm releases
            try:
                releases = json.loads(result.stdout)
                if not releases:
                    click.echo(f"      ⚠️  No Helm releases found in namespace {namespace}")
                    return
                
                # Uninstall all releases in this namespace
                for release in releases:
                    release_name = release.get('name', '')
                    if release_name:
                        uninstall_result = subprocess.run(
                            ['helm', 'uninstall', release_name, '--namespace', namespace],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        if uninstall_result.returncode == 0:
                            click.echo(f"      ✅ {service_name} - {release_name} destroyed (namespace: {namespace})")
                    else:
                            click.echo(f"      ⚠️  {service_name} - {release_name} not found or already destroyed (namespace: {namespace})")
                
            except json.JSONDecodeError:
                click.echo(f"      ⚠️  Error parsing Helm releases for namespace {namespace}")
                
        except subprocess.TimeoutExpired:
            click.echo(f"      ⚠️  Timeout destroying {service_name}")
        except Exception as e:
            click.echo(f"      ❌ Error destroying {service_name}: {str(e)}")
    
    def _delete_custom_namespaces(self):
        """Delete custom namespaces created during deployment"""
        click.echo("  🗂️  Cleaning up custom namespaces...")
        
        # List of namespaces that might have been created
        custom_namespaces = [
            'vault',
            'datahub',
            'elastic-system',
            'cert-manager',
            'traefik-ingress',
            'stackgres',
            'monitoring',
            'logging',
            'external-dns',
            'global-postgresql',
            'k8s-cleanup',
            'sso-keycloak',
            'pvc-autoscaler',
            'cicd-workload-trigger',
            'minio',
            'cicd-workflows',
            'data-replication',
            'data-orchestration',
            'data-modeling',
            'data-dcdq-metacollect',
            'data-analysis',
            'data-governance',
            'user-console'
        ]
        
        for namespace in custom_namespaces:
            try:
                result = subprocess.run(
                    ['kubectl', 'delete', 'namespace', namespace],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    click.echo(f"    ✅ Namespace {namespace} deleted")
                else:
                    click.echo(f"    ⚠️  Namespace {namespace} not found or already deleted")
                    
            except subprocess.TimeoutExpired:
                click.echo(f"    ⚠️  Timeout deleting namespace {namespace}")
            except Exception as e:
                click.echo(f"    ❌ Error deleting namespace {namespace}: {str(e)}")
    
    def _destroy_cloud_infrastructure(self):
        """Destroy cloud infrastructure using Terraform/Terragrunt"""
        click.echo("☁️  Step 2: Destroying cloud infrastructure...")
        
        cloud_provider = self.state.config.get('cloud_provider')
        if not cloud_provider:
            click.echo("⚠️  No cloud provider configured. Skipping infrastructure destruction.")
            return
        
        try:
            if cloud_provider == 'gcp':
                self._destroy_gcp_infrastructure()
            elif cloud_provider == 'aws':
                self._destroy_aws_infrastructure()
            elif cloud_provider == 'azure':
                self._destroy_azure_infrastructure()
            else:
                click.echo(f"⚠️  Unsupported cloud provider: {cloud_provider}")
                
        except Exception as e:
            click.echo(f"❌ Error destroying cloud infrastructure: {str(e)}")
            click.echo("⚠️  You may need to manually destroy infrastructure resources")
    
    def _destroy_gcp_infrastructure(self):
        """Destroy GCP infrastructure using Terragrunt"""
        click.echo("  🗑️  Destroying GCP infrastructure...")
        
        # Navigate to GCP Terraform directory
        terraform_dir = "terraform/google_cloud/terragrunt/bi-platform"
        if not Path(terraform_dir).exists():
            click.echo(f"    ⚠️  Terraform directory not found: {terraform_dir}")
            return
        
        # Change to terraform directory
        original_dir = os.getcwd()
        os.chdir(terraform_dir)
        
        try:
            # Run terragrunt destroy --all with non-interactive flag
            click.echo("    🔧 Running 'terragrunt destroy --all --non-interactive'...")
            result = subprocess.run(
                ['terragrunt', 'destroy', '--all', '--non-interactive'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                click.echo("    ✅ GCP infrastructure destroyed successfully")
            else:
                click.echo(f"    ❌ Error destroying GCP infrastructure: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            click.echo("    ⚠️  Timeout destroying GCP infrastructure")
        except Exception as e:
            click.echo(f"    ❌ Error destroying GCP infrastructure: {str(e)}")
        finally:
            # Change back to original directory
            os.chdir(original_dir)
    
    def _destroy_aws_infrastructure(self):
        """Destroy AWS infrastructure using Terraform"""
        click.echo("  🗑️  Destroying AWS infrastructure...")
        click.echo("    ⚠️  AWS infrastructure destruction not implemented yet")
        # TODO: Implement AWS infrastructure destruction
    
    def _destroy_azure_infrastructure(self):
        """Destroy Azure infrastructure using Terraform"""
        click.echo("  🗑️  Destroying Azure infrastructure...")
        click.echo("    ⚠️  Azure infrastructure destruction not implemented yet")
        # TODO: Implement Azure infrastructure destruction
    
    def _cleanup_state(self):
        """Clean up state and configuration files"""
        click.echo("🧹 Step 3: Cleaning up state and configuration...")
        
        try:
            # Delete state file
            if Path(self.state_file).exists():
                os.remove(self.state_file)
                click.echo("  ✅ State file deleted")
            
            # Delete kubeconfig file if it was created
            kubeconfig_path = self.state.kubeconfig_path
            if kubeconfig_path and Path(kubeconfig_path).exists():
                os.remove(kubeconfig_path)
                click.echo("  ✅ Kubeconfig file deleted")
            
            # Clean up any other temporary files
            self._cleanup_temp_files()
            
            click.echo("  ✅ Cleanup completed")
            
        except Exception as e:
            click.echo(f"  ❌ Error during cleanup: {str(e)}")
    
    def _cleanup_temp_files(self):
        """Clean up temporary files created during deployment"""
        # Only remove .terraform.lock.hcl files (these are safe to remove and will be regenerated)
        temp_files = [
            ".terraform.lock.hcl"
        ]
        
        # Get customer name from state for state file preservation
        customer = self.state.config.get('customer', '') if hasattr(self, 'state') and self.state.config else ''
        
        for temp_file in temp_files:
            if Path(temp_file).exists():
                try:
                    if Path(temp_file).is_dir():
                        import shutil
                        shutil.rmtree(temp_file)
                    else:
                        os.remove(temp_file)
                except Exception:
                    pass  # Ignore cleanup errors for temp files
        
        # Handle .terraform directories carefully to preserve state files
        if Path(".terraform").exists():
            if customer:
                # Check if this .terraform directory contains customer state files
                customer_state_dir = Path(".terraform") / customer
                if customer_state_dir.exists():
                    click.echo(f"  ℹ️  Preserving .terraform directory with state files for customer: {customer}")
                else:
                    # This .terraform directory doesn't contain our customer's state files, safe to remove
                    try:
                        import shutil
                        shutil.rmtree(".terraform")
                        click.echo("  ✅ Removed .terraform directory without state files")
                    except Exception:
                        pass  # Ignore cleanup errors for temp files
            else:
                # No customer info, be conservative and preserve .terraform
                click.echo("  ℹ️  Preserving .terraform directory (no customer info available)")
        
        # Note: terraform.tfstate and terraform.tfstate.backup files are preserved
        # as they contain important state information for local state deployments


def deploy_environment(config: Optional[str], interactive: Optional[bool], phase: Optional[int], simple_input: bool, state_file: str, show_config: bool, keycloak_help: bool, non_interactive: bool, destroy: bool, destroy_confirm: bool):
    """Deploy Fast.BI environment with configuration file or interactive setup."""
    
    try:
        # Initialize deployment state
        state = DeploymentState()
        state.load_state(state_file)
        
        # Handle destroy operation
        if destroy:
            if not destroy_confirm:
                click.echo("⚠️  WARNING: This will destroy the entire environment!")
                click.echo("   This includes:")
                click.echo("   - All Kubernetes resources (Helm charts, namespaces)")
                click.echo("   - Cloud infrastructure (GCP/AWS/Azure resources)")
                click.echo("   - All data and configurations")
                click.echo("")
                confirm = click.confirm("Are you sure you want to proceed with destruction?", default=False)
                if not confirm:
                    click.echo("❌ Destruction cancelled")
                    return
            
            click.echo("🗑️  Starting environment destruction...")
            destroy_manager = EnvironmentDestroyer(state_file)
            destroy_manager.destroy_environment()
            return
        
        # Determine if we should run in non-interactive mode
        run_non_interactive = non_interactive or (config and not interactive)
        
        # Handle show-config option
        if show_config:
            if not state.config:
                click.echo("❌ No deployment configuration found. Please run a deployment first.")
                return
            
            deployment = DeploymentManager(state)
            deployment.show_configuration_summary()
            return
        
        # Handle keycloak-help option
        if keycloak_help:
            if not state.config:
                click.echo("❌ No deployment configuration found. Please run a deployment first.")
                return
            
            deployment = DeploymentManager(state)
            deployment._show_keycloak_setup_help()
            return
        
        # Load configuration from file if provided
        if config:
            click.echo(f"\n📂 Loading configuration from {config}")
            if not Path(config).exists():
                click.echo(f"❌ Configuration file not found: {config}")
                return
            
            # Load configuration and update state
            config_data = load_config_from_file(config)
            state.config.update(config_data)
            state.save_state(state_file)
            click.echo("✅ Configuration loaded successfully")
        
        # In non-interactive mode, skip all user prompts
        if run_non_interactive:
            if not state.config:
                click.echo("❌ No configuration found. Please provide a configuration file.")
                return
            
            click.echo("\n🤖 Running in non-interactive mode...")
            
            # Check if we should skip confirmations
            skip_confirmations = state.config.get('skip_confirmations', False)
            if skip_confirmations:
                click.echo("⚠️  Skipping confirmations as configured")
            else:
                click.echo("ℹ️  Confirmations will be shown for critical steps (e.g., Keycloak configuration)")
            
            # Create deployment manager
            deployment = DeploymentManager(state, config_file=config, non_interactive=True)
            
            # Determine which phases to run
            phases_to_run = state.config.get('phases_to_run', 'all')
            if phases_to_run == 'all':
                phases_to_run = list(range(1, 7))
            elif isinstance(phases_to_run, str):
                phases_to_run = [int(p.strip()) for p in phases_to_run.split(',')]
            
            # Run phases
            for phase_num in phases_to_run:
                if not deployment.run_phase(phase_num):
                    click.echo(f"❌ Phase {phase_num} failed")
                    return
            
            click.echo("\n✅ Non-interactive deployment completed successfully!")
            return
        
        # Interactive mode
        click.echo("\n🚀 Fast.BI Platform Deployment CLI")
        
        # Check if there's an existing deployment state to show
        if state.config and any([state.infrastructure_deployed, state.secrets_generated, state.repositories_configured, 
                                state.infra_services_deployed, state.data_services_deployed, state.deployment_finalized]):
            click.echo("\n📋 Existing Deployment Found:")
            click.echo(f"  Customer: {state.config.get('customer', 'Not set')}")
            click.echo(f"  Email: {state.config.get('user_email', 'Not set')}")
            click.echo(f"  Cloud Provider: {state.config.get('cloud_provider', 'Not set')}")
            click.echo(f"  Domain: {state.config.get('domain_name', 'Not set')}")
            click.echo(f"  Terraform State: {state.config.get('gcp_terraform_state', 'Not set')}")
            click.echo(f"  Infrastructure Deployed: {'✅' if state.infrastructure_deployed else '❌'}")
            click.echo(f"  Secrets Generated: {'✅' if state.secrets_generated else '❌'}")
            click.echo(f"  Repositories Configured: {'✅' if state.repositories_configured else '❌'}")
            click.echo(f"  Infra Services Deployed: {'✅' if state.infra_services_deployed else '❌'}")
            click.echo(f"  Data Services Deployed: {'✅' if state.data_services_deployed else '❌'}")
            click.echo(f"  Deployment Finalized: {'✅' if state.deployment_finalized else '❌'}")
        else:
            click.echo("\n📋 No existing deployment found")
        
        # Ask user what they want to do
        choice = safe_select(
            "What would you like to do?",
            [
                "Start new deployment",
                "Continue existing deployment",
                "Exit"
            ]
        )
        
        if choice == "Exit":
            click.echo("👋 Goodbye!")
            return
        elif choice == "Start new deployment":
            # Clear the state
            state = DeploymentState()
            click.echo("🗑️ Starting fresh deployment")
        elif choice == "Continue existing deployment":
            if not state.config:
                click.echo("❌ No existing deployment to continue. Starting fresh.")
                state = DeploymentState()
            else:
                click.echo("✅ Continuing existing deployment")
        
        # Load or collect configuration
        if not state.config:
            state.config = collect_basic_config(use_simple_input=simple_input)
            state.save_state(state_file)
        else:
            click.echo("✅ Using existing configuration from state file")

        # Show deployment configuration summary
        if state.config:
            # Only show configuration if the new parameters are actually set
            terraform_state = state.config.get('gcp_terraform_state')
            gke_deployment_type = state.config.get('gcp_gke_deployment_type')
            
            if terraform_state and gke_deployment_type:
                click.echo("🎯 Deployment Configuration:")
                click.echo(f"   • State Backend: {terraform_state.upper()}")
                click.echo(f"   • GKE Type: {gke_deployment_type.upper()}")
                
                if terraform_state == 'local':
                    click.echo("   • Note: Infrastructure files will be saved locally")
                if gke_deployment_type == 'zonal':
                    click.echo("   • Note: Single zone deployment (cheaper/faster)")
                elif gke_deployment_type == 'multizone':
                    click.echo("   • Note: Multi-zone deployment (production-ready)")
            else:
                click.echo("🎯 Deployment Configuration: Basic configuration loaded")
                click.echo("   • State Backend: Will be configured during deployment")
                click.echo("   • GKE Type: Will be configured during deployment")

        # Show current state (only if we have config and not in initial choice)
        if state.config:
            deployment = DeploymentManager(state)
            deployment.show_deployment_status()

        # Create deployment manager
        deployment = DeploymentManager(state)
        
        # Run specific phase or all phases
        if phase:
            success = deployment.run_phase(phase)
        else:
            if safe_select("Run all phases or specific phase?", ['All phases', 'Specific phase']) == 'All phases':
                success = deployment.run_all_phases()
            else:
                # Show phase descriptions
                click.echo("\n📋 Available Phases:")
                click.echo("  1. Infrastructure Deployment - Deploy cloud infrastructure")
                click.echo("  2. Generate Platform Secrets - Create platform secrets and SSH keys")
                click.echo("  3. Configure Repositories - Set up data platform repositories")
                click.echo("  4. Deploy Infrastructure Services - Deploy Kubernetes infrastructure services")
                click.echo("  5. Deploy Data Services - Deploy data platform services")
                click.echo("  6. Finalize Deployment - Save deployment files to repository")
                click.echo("")
                phase_num = int(safe_input("Enter phase number (1-6)", validate=lambda x: x.isdigit() and 1 <= int(x) <= 6))
                success = deployment.run_phase(phase_num)
        
        if success:
            state.save_state(state_file)
            click.echo(f"\n✅ Deployment completed successfully! State saved to {state_file}")
        else:
            click.echo(f"\n❌ Deployment failed! State saved to {state_file}")

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        raise click.Abort()

@click.command()
@click.option('--config', '-c', type=str, help='Path to configuration file (YAML)')
@click.option('--interactive/--no-interactive', default=None, help='Run in interactive mode')
@click.option('--phase', type=int, help='Execute specific phase only (1-6): 1=Infrastructure, 2=Secrets, 3=Repositories, 4=Infra Services, 5=Data Services, 6=Finalize')
@click.option('--simple-input', is_flag=True, help='Use simple input method (better for pasting)')
@click.option('--state-file', type=str, default='cli/state/deployment_state.json', help='Path to state file')
@click.option('--show-config', is_flag=True, help='Show configuration summary and exit')
@click.option('--keycloak-help', is_flag=True, help='Show Keycloak setup help and exit')
@click.option('--non-interactive', is_flag=True, help='Run in non-interactive mode (requires config file)')
@click.option('--destroy', is_flag=True, help='Destroy entire environment (infrastructure + Kubernetes resources)')
@click.option('--destroy-confirm', is_flag=True, help='Skip confirmation for destroy operation')
def cli(config: Optional[str], interactive: Optional[bool], phase: Optional[int], simple_input: bool, state_file: str, show_config: bool, keycloak_help: bool, non_interactive: bool, destroy: bool, destroy_confirm: bool):
    """Fast.BI Platform Deployment CLI"""
    deploy_environment(config, interactive, phase, simple_input, state_file, show_config, keycloak_help, non_interactive, destroy, destroy_confirm)


if __name__ == '__main__':
    cli()