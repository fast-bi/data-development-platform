import os
import shutil
import logging
import subprocess
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import sys
import base64
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('infrastructure_deployment.log')
    ]
)
logger = logging.getLogger('infrastructure_deployment_operator')

class InfrastructureDeploymentError(Exception):
    """Base exception for infrastructure deployment errors"""
    pass

class VaultError(InfrastructureDeploymentError):
    """Exception raised for vault-related errors"""
    pass

class GitError(InfrastructureDeploymentError):
    """Exception raised for git-related errors"""
    pass

class InfrastructureDeploymentOperator:
    """
    Handles infrastructure deployment file collection, encryption, and storage in Git repositories.
    Supports multiple cloud providers and git providers with flexible credential management.
    """
    
    def __init__(self, 
                 customer: str,
                 method: str = "local_vault",
                 cloud_provider: str = "gcp",
                 terraform_state: str = "remote",
                 # Git configuration
                 git_provider: Optional[str] = None,
                 git_repo_url: Optional[str] = None,
                 git_access_token: Optional[str] = None,
                 git_private_key: Optional[str] = None,
                 git_username: Optional[str] = None,
                 git_password: Optional[str] = None,
                 # Vault configuration
                 vault_project_id: Optional[str] = None,
                 secret_manager_client_id: Optional[str] = None,
                 secret_manager_client_secret: Optional[str] = None,
                 # Kubernetes configuration
                 kube_config_path: Optional[str] = None,
                 namespace: str = "vault",
                 # Operation flags
                 force_deployment: bool = False,
                 cleanup_enabled: bool = True):
        """
        Initialize the InfrastructureDeploymentOperator.
        
        Args:
            customer: Customer name
            method: Vault method ('local_vault' or 'external_infisical')
            cloud_provider: Cloud provider ('gcp', 'aws', 'azure', 'self-managed')
            terraform_state: Terraform state storage ('local' or 'remote')
            git_provider: Git provider (auto-detected if not provided)
            git_repo_url: Git repository URL
            git_access_token: Git access token
            git_private_key: Path to Git private key file
            git_username: Git username
            git_password: Git password
            vault_project_id: Vault project ID
            secret_manager_client_id: Secret manager client ID
            secret_manager_client_secret: Secret manager client secret
            kube_config_path: Path to kubeconfig file
            namespace: Kubernetes namespace for vault
            force_deployment: Force deployment even if no infrastructure files are found
            cleanup_enabled: Enable cleanup of local environment after deployment
        """
        logger.info(f"Initializing InfrastructureDeploymentOperator for customer: {customer}")
        
        # Core configuration
        self.customer = customer
        self.method = method
        self.cloud_provider = cloud_provider
        self.terraform_state = terraform_state
        
        # Git configuration
        self.git_provider = git_provider
        self.git_repo_url = git_repo_url
        self.git_access_token = git_access_token
        self.git_private_key = git_private_key
        self.git_username = git_username
        self.git_password = git_password
        
        # Vault configuration
        self.vault_project_id = vault_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        
        # Kubernetes configuration
        self.kube_config_path = kube_config_path
        self.namespace = namespace
        
        # Operation flags
        self.force_deployment = force_deployment
        self.cleanup_enabled = cleanup_enabled
        
        # Working directory
        self.working_dir = f"/tmp/{customer}_infrastructure_deployment_files"
        
        # Validate configuration
        self._validate_configuration()
        
        # Initialize components
        self._initialize_components()
        
    def _validate_configuration(self):
        """Validate the configuration parameters"""
        logger.info("Validating configuration parameters")
        
        # Validate customer name
        if not self.customer or not self.customer.strip():
            raise ValueError("Customer name is required and cannot be empty")
        
        # Validate cloud provider
        if self.cloud_provider not in ['gcp', 'aws', 'azure', 'self-managed']:
            raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
            
        # Validate method
        if self.method not in ['local_vault', 'external_infisical']:
            raise ValueError(f"Unsupported method: {self.method}")
            
        # Validate terraform_state
        if self.terraform_state not in ['local', 'remote']:
            raise ValueError(f"Unsupported terraform_state: {self.terraform_state}")
            
        # Validate method-specific requirements
        if self.method == "external_infisical":
            if not all([self.vault_project_id, self.secret_manager_client_id, self.secret_manager_client_secret]):
                raise ValueError("vault_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
                
        # Validate git configuration
        if not self.git_repo_url:
            raise ValueError("git_repo_url is required")
            
        logger.info("Configuration validation completed successfully")
        
    def _validate_encryption_key(self):
        """Validate that the encryption key is properly formatted"""
        try:
            # Test the encryption key by creating a Fernet instance
            fernet = Fernet(self.encryption_key.encode('utf-8'))
            # Try to encrypt a small test string
            test_data = b"test"
            encrypted = fernet.encrypt(test_data)
            decrypted = fernet.decrypt(encrypted)
            if decrypted != test_data:
                raise ValueError("Encryption key validation failed - decryption mismatch")
            logger.debug("Encryption key validation successful")
        except Exception as e:
            logger.error(f"Encryption key validation failed: {str(e)}")
            raise InfrastructureDeploymentError(f"Invalid encryption key: {str(e)}")

    def _initialize_components(self):
        """Initialize required components based on configuration"""
        logger.info("Initializing components")
        
        try:
            # Initialize encryption
            self.encryption_key = Fernet.generate_key().decode('utf-8')
            logger.info("Encryption key generated successfully")
            
            # Validate encryption key
            self._validate_encryption_key()
            logger.info("Encryption key validated successfully")
            
            # Initialize vault client first
            self.vault_client = self._initialize_vault_client()
            logger.info("Vault client initialized successfully")
            
            # Initialize git manager after vault client is ready
            self.git_manager = self._initialize_git_manager()
            logger.info("Git manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            raise InfrastructureDeploymentError(f"Component initialization failed: {str(e)}")
            
    def _initialize_git_manager(self):
        """Initialize git manager with appropriate authentication"""
        if not self.git_provider:
            self.git_provider = self._detect_git_provider(self.git_repo_url)
            
        # If git_access_token is not provided, try to get it from vault
        if not self.git_access_token:
            logger.info(f"No access token provided, attempting to retrieve from vault for {self.git_provider}")
            try:
                self.git_access_token = self._get_git_access_token_from_vault()
                logger.info(f"Retrieved {self.git_provider} access token from vault")
            except Exception as e:
                logger.error(f"Failed to get {self.git_provider} access token from vault: {str(e)}")
                raise ValueError(f"{self.git_provider.capitalize()} access token is required. Either provide it directly via --git_access_token parameter or ensure it exists in vault")
        else:
            logger.info(f"Using provided {self.git_provider} access token")
            
        # Validate git credentials based on provider
        self._validate_git_credentials()
        
        return GitManager(
            repo_url=self.git_repo_url,
            credentials=self._get_git_credentials(),
            working_dir=self.working_dir
        )
        
    def _initialize_vault_client(self):
        """Initialize vault client based on method"""
        if self.method == "external_infisical":
            if not all([self.vault_project_id, self.secret_manager_client_id, self.secret_manager_client_secret]):
                raise ValueError("vault_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
            return ExternalInfisicalClient(
                project_id=self.vault_project_id,
                client_id=self.secret_manager_client_id,
                client_secret=self.secret_manager_client_secret
            )
        else:
            self.secret_file = f"/tmp/{self.customer}_customer_vault_structure.json"
            logger.info(f"Looking for secret file: {self.secret_file}")
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")
            logger.info(f"Secret file found: {self.secret_file}")
            return LocalVaultClient(
                customer=self.customer,
                kube_config=self.kube_config_path,
                namespace=self.namespace
            )
            
    def _validate_git_credentials(self):
        """Validate git credentials based on provider"""
        if self.git_provider in ['github', 'gitlab', 'bitbucket']:
            if not (self.git_access_token or (self.git_private_key and self.git_username)):
                raise ValueError(f"Either access token or private key + username required for {self.git_provider}")
        elif self.git_provider == 'gitea':
            if not (self.git_access_token or (self.git_username and self.git_password)):
                raise ValueError("Either access token or username + password required for Gitea")
        else:
            raise ValueError(f"Unsupported git provider: {self.git_provider}")
                
    def _get_git_credentials(self) -> Dict:
        """Get git credentials based on provider"""
        credentials = {}
        
        if self.git_access_token:
            credentials['access_token'] = self.git_access_token
        elif self.git_private_key:
            credentials['private_key'] = self.git_private_key
            credentials['username'] = self.git_username
        else:
            credentials['username'] = self.git_username
            credentials['password'] = self.git_password
            
        return credentials
        
    def _detect_git_provider(self, repo_url: str) -> str:
        """Detect git provider from repository URL"""
        if not repo_url:
            return "gitlab"  # Default provider
            
        url = repo_url.lower()
        
        if "github" in url:
            return "github"
        elif "gitlab" in url:
            return "gitlab"
        elif "gitea" in url:
            return "gitea"
        elif "bitbucket" in url:
            return "bitbucket"
        else:
            return "gitlab"  # Default provider
            
    def _copy_template_files(self):
        """Copy template files to the repository"""
        logger.info("Copying template files to repository")
        
        try:
            # Define template source directory
            template_dir = os.path.join(os.path.dirname(__file__), 'templates', 'git_repo_templates', 'infrastructure_deployment_files')
            
            # Copy template files
            for file in ['README.md', 'encrypt_files.py', 'decrypt_files.py']:
                source_path = os.path.join(template_dir, file)
                target_path = os.path.join(self.working_dir, file)
                
                if os.path.exists(source_path):
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Copied template file: {file}")
                else:
                    logger.warning(f"Template file not found: {file}")
                    
        except Exception as e:
            logger.error(f"Failed to copy template files: {str(e)}")
            raise InfrastructureDeploymentError(f"Template file copy failed: {str(e)}")

    def collect_and_store_infrastructure(self):
        """Main method to collect and store infrastructure files"""
        logger.info(f"Starting infrastructure collection for customer: {self.customer}")
        
        try:
            # Create working directory
            os.makedirs(self.working_dir, exist_ok=True)
            logger.info(f"Created working directory: {self.working_dir}")
            
            # Clone repository
            self.git_manager.clone_repository()
            logger.info("Repository cloned successfully")
            
            # Copy template files
            self._copy_template_files()
            logger.info("Template files copied successfully")
            
            # Get infrastructure mappings
            mappings = self._get_infrastructure_mappings()
            logger.info("Retrieved infrastructure mappings")
            
            # Check for Terraform state files if terraform_state is local
            if self.terraform_state == "local":
                self._check_terraform_state_files(mappings)
            
            # Check what files exist and provide summary
            total_files = 0
            existing_files = 0
            
            for mapping_type, mapping in mappings.items():
                for directory, files in mapping.items():
                    for file in files:
                        total_files += 1
                        if os.path.exists(self._get_source_path(directory, file)):
                            existing_files += 1
            
            logger.info(f"Infrastructure scan complete: {existing_files}/{total_files} files found")
            
            if existing_files == 0:
                logger.info("No infrastructure files found - this appears to be a manual deployment")
            else:
                logger.info(f"Found {existing_files} infrastructure files to process")
                if existing_files < total_files:
                    logger.info(f"Note: {total_files - existing_files} files are missing from the expected mapping")
                    logger.info("This is normal if some Terraform modules haven't been applied yet or some files are optional")
            
            # Always proceed with validation and processing - validation is now more flexible
            # Note: We don't need to validate here since we check file existence during processing
            logger.info("Core infrastructure files validation skipped - will validate during processing")
            
            # Prepare and encrypt files
            self._prepare_and_encrypt_files(mappings)
            logger.info("Files prepared and encrypted")
            
            # Save encryption key to vault
            self.save_encryption_key()
            logger.info("Encryption key saved to vault")
            
            # Check if we have any encrypted files to commit
            encrypted_files = []
            for root, dirs, files in os.walk(self.working_dir):
                for file in files:
                    if not file.startswith('.') and file not in ['README.md', 'encrypt_files.py', 'decrypt_files.py']:
                        encrypted_files.append(os.path.join(root, file))
            
            if not encrypted_files:
                if self.force_deployment:
                    logger.warning("No infrastructure files were processed, but force_deployment is enabled - proceeding with empty repository")
                else:
                    logger.warning("No infrastructure files were processed - repository will not be updated")
                    return self._get_deployment_summary()
            
            logger.info(f"Found {len(encrypted_files)} encrypted files to commit")
            
            # Commit and push changes
            self._commit_and_push_changes()
            logger.info("Changes committed and pushed")
            
            # Clean up local environment after successful deployment
            if self.cleanup_enabled:
                self._cleanup_local_environment()
                logger.info("Local environment cleaned up")
            else:
                logger.info("Local environment cleanup skipped (cleanup_enabled=False)")
            
            # Cleanup
            self._cleanup()
            logger.info("Cleanup completed")
            
            return self._get_deployment_summary()
            
        except Exception as e:
            logger.error(f"Failed to collect and store infrastructure: {str(e)}")
            self._cleanup()  # Ensure cleanup on failure
            raise InfrastructureDeploymentError(f"Infrastructure collection failed: {str(e)}")
            
    def _get_infrastructure_mappings(self) -> Dict:
        """Get infrastructure file mappings based on cloud provider"""
        mappings = {
            'core_infrastructure': self._get_core_infrastructure_mapping(),
            'k8s_core_services': self._get_k8s_core_services_mapping(),
            'k8s_data_services': self._get_k8s_data_services_mapping()
        }
        return mappings
        
    def _get_core_infrastructure_mapping(self) -> Dict:
        """Get core infrastructure mapping based on cloud provider"""
        if self.cloud_provider == "gcp":
            mapping = {
                '.': ['.gitignore', 'defaults.yaml', 'empty.yaml', f'{self.customer}_deployment.log'],
                'bi-platform': ['terragrunt.hcl', 'backend.tf', 'env.yaml'],
                'bi-platform/00-create-ou-folder': ['terragrunt.hcl'],
                'bi-platform/01-create-project': ['terragrunt.hcl'],
                'bi-platform/02-enable-apis': ['terragrunt.hcl'],
                'bi-platform/03-0-apps-vpc': ['terragrunt.hcl'],
                'bi-platform/04-external-ip-traefik': ['terragrunt.hcl', 'external_ip_traefik.txt'],
                'bi-platform/05-create-dns-zone': ['terragrunt.hcl', 'dns_zone_complete_info.txt', 'dns_zone_nameservers.txt'],
                'bi-platform/06-create-dns-ns-record': ['terragrunt.hcl'],
                'bi-platform/07-gke-cluster': ['terragrunt.hcl'],
                'bi-platform/08-dbt_deploy_sa': ['terragrunt.hcl', 'sa_key.txt', 'sa_name.txt'],
                'bi-platform/09-dbt_sa': ['terragrunt.hcl', 'sa_name.txt'],
                'bi-platform/10-cert_manager_sa': ['terragrunt.hcl', 'sa_name.txt'],
                'bi-platform/11-external_dns_sa': ['terragrunt.hcl', 'sa_name.txt'],
                'bi-platform/12-monitoring_sa': ['terragrunt.hcl', 'sa_name.txt'],
                'bi-platform/13-data_replication_sa': ['terragrunt.hcl', 'sa_name.txt'],
                'bi-platform/14-data_orchestration_sa': ['terragrunt.hcl', 'sa_name.txt'],
                'bi-platform/15-bi_data_sa': ['terragrunt.hcl', 'sa_key.txt', 'sa_name.txt'],
                'bi-platform/16-whitelist-external-ip-on-common': ['terragrunt.hcl'],
                'bi-platform/17-kubeconfig': ['terragrunt.hcl', 'kubeconfig']
            }
            
            # Add .terraform folders and state files if terraform_state is local
            if self.terraform_state == "local":
                terraform_folders = [
                    'bi-platform/00-create-ou-folder',
                    'bi-platform/01-create-project',
                    'bi-platform/02-enable-apis',
                    'bi-platform/03-0-apps-vpc',
                    'bi-platform/04-external-ip-traefik',
                    'bi-platform/05-create-dns-zone',
                    'bi-platform/06-create-dns-ns-record',
                    'bi-platform/07-gke-cluster',
                    'bi-platform/08-dbt_deploy_sa',
                    'bi-platform/09-dbt_sa',
                    'bi-platform/10-cert_manager_sa',
                    'bi-platform/11-external_dns_sa',
                    'bi-platform/12-monitoring_sa',
                    'bi-platform/13-data_replication_sa',
                    'bi-platform/14-data_orchestration_sa',
                    'bi-platform/15-bi_data_sa',
                    'bi-platform/16-whitelist-external-ip-on-common',
                    'bi-platform/17-kubeconfig'
                ]
                
                for folder in terraform_folders:
                    mapping[f'{folder}/.terraform/{self.customer}/{folder.split("/")[-1]}'] = ['terraform.tfstate', 'terraform.tfstate.backup']
                    
            return mapping
        elif self.cloud_provider == "aws":
            mapping = {
                '.': ['.gitignore', 'defaults.yaml', 'empty.yaml', f'{self.customer}_deployment.log'],
                'bi-platform': ['terragrunt.hcl', 'backend.tf', 'env.yaml'],
                'bi-platform/01-enable-apis': ['terragrunt.hcl'],
                'bi-platform/02-apps-vpc': ['terragrunt.hcl'],
                'bi-platform/03-external-ip-traefik': ['terragrunt.hcl'],
                'bi-platform/04-create-dns-zone': ['terragrunt.hcl'],
                'bi-platform/05-create-dns-ns-record': ['terragrunt.hcl'],
                'bi-platform/06-eks-cluster': ['terragrunt.hcl'],
                'bi-platform/07-eks-cluster-artifact-registry-access': ['terragrunt.hcl'],
                'bi-platform/08-whitelist-external-ip-on-common': ['terragrunt.hcl']
            }
            
            # Add .terraform folders and state files if terraform_state is local
            if self.terraform_state == "local":
                terraform_folders = [
                    'bi-platform/01-enable-apis',
                    'bi-platform/02-apps-vpc',
                    'bi-platform/03-external-ip-traefik',
                    'bi-platform/04-create-dns-zone',
                    'bi-platform/05-create-dns-ns-record',
                    'bi-platform/06-eks-cluster',
                    'bi-platform/07-eks-cluster-artifact-registry-access',
                    'bi-platform/08-whitelist-external-ip-on-common'
                ]
                
                for folder in terraform_folders:
                    mapping[f'{folder}/.terraform'] = ['terraform.tfstate', 'terraform.tfstate.backup']
                    
            return mapping
        elif self.cloud_provider == "azure":
            mapping = {
                '.': ['.gitignore', 'defaults.yaml', 'empty.yaml', f'{self.customer}_deployment.log'],
                'bi-platform': ['terragrunt.hcl', 'backend.tf', 'env.yaml'],
                'bi-platform/01-enable-apis': ['terragrunt.hcl'],
                'bi-platform/02-apps-vpc': ['terragrunt.hcl'],
                'bi-platform/03-external-ip-traefik': ['terragrunt.hcl'],
                'bi-platform/04-create-dns-zone': ['terragrunt.hcl'],
                'bi-platform/05-create-dns-ns-record': ['terragrunt.hcl'],
                'bi-platform/06-aks-cluster': ['terragrunt.hcl'],
                'bi-platform/07-aks-cluster-artifact-registry-access': ['terragrunt.hcl'],
                'bi-platform/08-whitelist-external-ip-on-common': ['terragrunt.hcl']
            }
            
            # Add .terraform folders and state files if terraform_state is local
            if self.terraform_state == "local":
                terraform_folders = [
                    'bi-platform/01-enable-apis',
                    'bi-platform/02-apps-vpc',
                    'bi-platform/03-external-ip-traefik',
                    'bi-platform/04-create-dns-zone',
                    'bi-platform/05-create-dns-ns-record',
                    'bi-platform/06-aks-cluster',
                    'bi-platform/07-aks-cluster-artifact-registry-access',
                    'bi-platform/08-whitelist-external-ip-on-common'
                ]
                
                for folder in terraform_folders:
                    mapping[f'{folder}/.terraform'] = ['terraform.tfstate', 'terraform.tfstate.backup']
                    
            return mapping
        else:  # self-managed
            return {}  # Empty mapping for self-managed as it's built manually

    def _get_k8s_core_services_mapping(self) -> Dict:
        """Get Kubernetes core services mapping"""
        return {
            'secret_manager': ['values.yaml', 'values_extra.yaml'],
            'secret_manager_operator': ['values.yaml', 'values_extra.yaml'],
            'cert_manager': ['values.yaml', 'values_extra.yaml'],
            'cluster_cleaner': ['values.yaml'],
            'external_dns': ['values.yaml'],
            'idp_sso_manager': [f'{self.customer}_realm.json', 'values.yaml'],
            'log_collector': ['values.yaml'],
            'pvc_autoscaller': ['values.yaml', 'values_extra.yaml'],
            'services_monitoring': ['alerts_cm.yaml', 'dashboard_cm.yaml', 'values.yaml'],
            'stackgres_postgres_db': ['values.yaml', 'values_extra.yaml'],
            'traefik_lb': ['values.yaml']
        }

    def _get_k8s_data_services_mapping(self) -> Dict:
        """Get Kubernetes data services mapping"""
        return {
            'argo_workflows': ['postgresql_values.yaml', 'values.yaml'],
            'cicd_workload_runner': ['values.yaml', 'values_extra.yaml'],
            'object_storage_operator': ['operator_values.yaml', 'values.yaml'],
            'data_analysis/lightdash': ['values.yaml'],
            'data_analysis/superset': ['values.yaml'],
            'data_analysis/metabase': ['values.yaml'],
            'data_analysis': ['postgresql_values.yaml', 'values.yaml'],
            'data_dbt_server': ['values.yaml'],
            'data_dcdq_metacollect': ['values.yaml', 'values_extra.yaml', 'postgresql_values.yaml'],
            'data_dcdq_metacollect/data_catalog': ['oauth2proxy_values.yaml'],
            'data_dcdq_metacollect/data_quality': ['oauth2proxy_values.yaml'],
            'data_governance': ['values.yaml', 'dh_values.yaml', 'dh_prerequisites_values.yaml', 
                              'eck_es_values.yaml', 'eck_operator_values.yaml', 'postgresql_values.yaml'],
            'data_modeling': ['values.yaml', 'postgresql_values.yaml', 'values_extra.yaml'],
            'data_orchestration': ['values.yaml', 'values_extra.yaml'],
            'data_replication': ['values.yaml', 'oauth2proxy_values.yaml', 'postgresql_values.yaml'],
            'user_console': ['values.yaml', 'postgresql_values.yaml']
        }
        
    def _check_terraform_state_files(self, mappings: Dict) -> Dict:
        """Check for existence of Terraform state files when terraform_state is local"""
        if self.terraform_state != "local":
            return {}
            
        logger.info("Checking for Terraform state files...")
        state_files_found = {}
        
        for mapping_type, mapping in mappings.items():
            if mapping_type == 'core_infrastructure':
                for directory, files in mapping.items():
                    if '.terraform' in directory:
                        existing_files = []
                        for file in files:
                            source_path = self._get_source_path(directory, file)
                            if os.path.exists(source_path):
                                existing_files.append(file)
                        
                        if existing_files:
                            state_files_found[directory] = existing_files
                            logger.info(f"Found Terraform state files in {directory}: {', '.join(existing_files)}")
                        else:
                            logger.warning(f"No Terraform state files found in {directory}")
        
        if state_files_found:
            logger.info(f"Found Terraform state files in {len(state_files_found)} directories")
        else:
            logger.warning("No Terraform state files found - this may indicate that Terraform has not been run yet")
            
        return state_files_found

    def _prepare_and_encrypt_files(self, mappings: Dict):
        """Prepare and encrypt files based on mappings, preserving logical structure under new root folders"""
        logger.info("Preparing and encrypting files")
        
        if self.terraform_state == "local":
            logger.info("Terraform state is set to 'local' - will include .terraform folders and state files")

        root_map = {
            'core_infrastructure': 'core-infrastructure-deployment',
            'k8s_core_services': 'k8s-infrastructure-services-deployment',
            'k8s_data_services': 'k8s-data-platform-services-deployment',
        }
        
        total_processed = 0
        total_files_in_mappings = 0
        
        for mapping_type, mapping in mappings.items():
            logger.info(f"Processing {mapping_type} mapping")
            root_folder = root_map.get(mapping_type, mapping_type)
            
            # Count files for this mapping type
            files_in_mapping = 0
            processed_in_mapping = 0
            missing_files = []
            
            for directory, files in mapping.items():
                for file in files:
                    files_in_mapping += 1
                    total_files_in_mappings += 1
                    source_path = self._get_source_path(directory, file)
                    if os.path.exists(source_path):
                        processed_in_mapping += 1
                        total_processed += 1
                        
                        # For services, preserve subfolder structure
                        if mapping_type == 'core_infrastructure':
                            target_dir = os.path.join(self.working_dir, root_folder, directory)
                        else:
                            target_dir = os.path.join(self.working_dir, root_folder, directory)
                        os.makedirs(target_dir, exist_ok=True)
                        target_path = os.path.join(target_dir, file)
                        self._encrypt_and_copy_file(source_path, target_path)
                        
                        # Special logging for Terraform state files
                        if '.terraform' in directory and file in ['terraform.tfstate', 'terraform.tfstate.backup']:
                            logger.info(f"Processed Terraform state file: {directory}/{file} -> {target_path}")
                        else:
                            logger.debug(f"Processed file: {directory}/{file} -> {target_path}")
                    else:
                        missing_files.append(f"{directory}/{file} (expected: {source_path})")
                        # Special logging for missing Terraform state files
                        if '.terraform' in directory and file in ['terraform.tfstate', 'terraform.tfstate.backup']:
                            logger.warning(f"Terraform state file not found: {source_path}")
                        else:
                            logger.debug(f"Source file not found: {source_path}")
            
            if processed_in_mapping > 0:
                logger.info(f"Completed {mapping_type}: {processed_in_mapping}/{files_in_mapping} files processed")
                if missing_files:
                    logger.warning(f"Missing {len(missing_files)} files in {mapping_type}: {', '.join(missing_files[:5])}{'...' if len(missing_files) > 5 else ''}")
            else:
                logger.info(f"No files found for {mapping_type} - skipping")
        
        logger.info(f"File processing complete: {total_processed}/{total_files_in_mappings} files encrypted and copied")
        logger.info(f"Total files in mappings: {total_files_in_mappings}, Total processed: {total_processed}, Missing: {total_files_in_mappings - total_processed}")
        
        # Add a clear summary
        success_rate = (total_processed / total_files_in_mappings * 100) if total_files_in_mappings > 0 else 0
        logger.info(f"File processing summary: {success_rate:.1f}% success rate ({total_processed}/{total_files_in_mappings} files)")
        
        if success_rate < 100:
            logger.warning(f"Some files were not found and could not be processed. This may be normal if:")
            logger.warning("- Some Terraform modules haven't been applied yet")
            logger.warning("- Some files are generated during deployment")
            logger.warning("- Some optional files are missing")
        else:
            logger.info("All expected files were successfully processed!")
                        
    def _get_source_path(self, directory: str, file: str) -> str:
        """Get source path for a file based on mapping type"""
        # Check if directory is a core service
        if directory in self._get_k8s_core_services_mapping():
            base_path = "charts/infra_services_charts"
        # Check if directory is a data service
        elif directory in self._get_k8s_data_services_mapping():
            base_path = "charts/data_services_charts"
        else:
            # Default for core infrastructure
            if self.cloud_provider == "gcp":
                base_path = "terraform/google_cloud/terragrunt"
            elif self.cloud_provider == "aws":
                base_path = "terraform/aws_cloud/terragrunt"
            elif self.cloud_provider == "azure":
                base_path = "terraform/azure_cloud/terragrunt"
            else:
                base_path = "terraform/self_managed/terragrunt"
        
        # Handle .terraform folders - they have a nested structure
        if '.terraform' in directory:
            # For .terraform folders, we need to handle the nested structure
            # The directory format is: bi-platform/01-create-project/.terraform/{customer}/01-create-project
            # We need to extract the parent directory and the final subdirectory
            parts = directory.split('/')
            if len(parts) >= 4 and parts[-3] == '.terraform' and parts[-2] == self.customer:
                # This is a terraform state file path
                parent_dir = '/'.join(parts[:-3])  # bi-platform/01-create-project
                sub_dir = parts[-1]  # 01-create-project
                return os.path.join(base_path, parent_dir, '.terraform', self.customer, sub_dir, file)
            else:
                # Fallback for other .terraform paths
                return os.path.join(base_path, directory, file)
        
        return os.path.join(base_path, directory, file)
        
    def _encrypt_and_copy_file(self, source_path: str, target_path: str):
        """Encrypt and copy a file"""
        try:
            logger.debug(f"Encrypting file: {source_path}")
            
            # Check if source file exists
            if not os.path.exists(source_path):
                logger.warning(f"Source file does not exist: {source_path}")
                return
            
            # Check if source file is readable
            if not os.access(source_path, os.R_OK):
                logger.warning(f"Source file is not readable: {source_path}")
                return
            
            # Check file size
            file_size = os.path.getsize(source_path)
            if file_size == 0:
                logger.warning(f"Source file is empty: {source_path}")
                return
            
            with open(source_path, 'rb') as f:
                content = f.read()
            
            # Validate content
            if not content:
                logger.warning(f"Source file has no content: {source_path}")
                return
                
            # Encrypt content
            fernet = Fernet(self.encryption_key.encode('utf-8'))
            encrypted_content = fernet.encrypt(content)
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Write encrypted content
            with open(target_path, 'wb') as f:
                f.write(encrypted_content)
                
            logger.debug(f"File encrypted and copied to: {target_path}")
            
        except Exception as e:
            logger.error(f"Failed to encrypt and copy file {source_path}: {str(e)}")
            # Don't raise the exception, just log it and continue
            # This prevents one bad file from stopping the entire process
            
    def save_encryption_key(self):
        """Save encryption key to vault and log it"""
        logger.info("Saving encryption key to vault")
        logger.info(f"Generated encryption key: {self.encryption_key}")
        
        try:
            if self.method == "external_infisical":
                if not self.vault_project_id or not self.secret_manager_client_id or not self.secret_manager_client_secret:
                    raise ValueError("For external_infisical method, vault_project_id, client_id, and client_secret are required")
                return self.vault_client.save_secret(
                    secret_name='infrastructure_value_files_encryption_key',
                    secret_value=self.encryption_key,
                    secret_path='/'
                )
            else:  # local_vault
                # Setup port forward to vault
                self.vault_client._setup_port_forward()
                
                try:
                    # Get vault token from Kubernetes secret
                    cmd = [
                        "kubectl", "get", "secret", "vault-init", "-n", self.vault_client.namespace,
                        "-o", "jsonpath={.data.root-token}"
                    ]
                    if self.kube_config_path:
                        cmd.extend(["--kubeconfig", self.kube_config_path])
                        
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    root_token = base64.b64decode(result.stdout).decode('utf-8')
                    
                    # Save secret using vault API
                    headers = {
                        "X-Vault-Token": root_token,
                        "Content-Type": "application/json"
                    }
                    
                    # Create the secret path
                    path = "/v1/secret/data/infrastructure_value_files_encryption_key"
                    payload = {
                        "data": {
                            "value": self.encryption_key
                        }
                    }
                    
                    response = requests.post(
                        f"{self.vault_client.vault_addr}{path}",
                        headers=headers,
                        json=payload,
                        timeout=10
                    )
                    response.raise_for_status()
                    
                    logger.info("Encryption key saved to vault successfully")
                    return response.json()
                    
                finally:
                    self.vault_client._cleanup_port_forward()
                
        except Exception as e:
            logger.error(f"Failed to save encryption key: {str(e)}")
            raise VaultError(f"Failed to save encryption key: {str(e)}")
            
    def _commit_and_push_changes(self):
        """Commit and push changes to git repository"""
        try:
            self.git_manager.commit_and_push("Update infrastructure files")
        except Exception as e:
            logger.error(f"Failed to commit and push changes: {str(e)}")
            raise
            
    def _cleanup(self):
        """Clean up temporary files and directories"""
        try:
            if os.path.exists(self.working_dir):
                logger.info(f"Cleaning up working directory: {self.working_dir}")
                shutil.rmtree(self.working_dir)
                logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.warning(f"Failed to cleanup working directory: {str(e)}")
            # Don't raise here as this is cleanup
            
    def _cleanup_local_environment(self):
        """Clean up local environment after successful deployment"""
        logger.info("Starting local environment cleanup...")
        
        try:
            # Clean up Terraform state files and sensitive data
            self._cleanup_terraform_files()
            
            # Clean up service account keys and sensitive files
            self._cleanup_sensitive_files()
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            # Clean up secret files
            self._cleanup_secret_files()
            
            logger.info("Local environment cleanup completed successfully")
            
        except Exception as e:
            logger.warning(f"Some cleanup operations failed: {str(e)}")
            # Don't raise here as this is cleanup
            
    def _cleanup_terraform_files(self):
        """Clean up Terraform state files and .terraform directories"""
        logger.info("Cleaning up Terraform files...")
        
        terraform_dirs_to_clean = [
            "terraform/google_cloud/terragrunt/bi-platform",
            "terraform/aws_cloud/terragrunt/bi-platform", 
            "terraform/azure_cloud/terragrunt/bi-platform"
        ]
        
        for base_dir in terraform_dirs_to_clean:
            if not os.path.exists(base_dir):
                continue
                
            for root, dirs, files in os.walk(base_dir):
                # Clean up .terraform directories
                if '.terraform' in dirs:
                    terraform_dir = os.path.join(root, '.terraform')
                    try:
                        shutil.rmtree(terraform_dir)
                        logger.debug(f"Removed .terraform directory: {terraform_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to remove .terraform directory {terraform_dir}: {str(e)}")
                
                # Clean up terraform.tfstate files
                for file in files:
                    if file in ['terraform.tfstate', 'terraform.tfstate.backup']:
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            logger.debug(f"Removed terraform state file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to remove terraform state file {file_path}: {str(e)}")
                            
    def _cleanup_sensitive_files(self):
        """Clean up sensitive files like service account keys"""
        logger.info("Cleaning up sensitive files...")
        
        terraform_dirs_to_clean = [
            "terraform/google_cloud/terragrunt/bi-platform",
            "terraform/aws_cloud/terragrunt/bi-platform",
            "terraform/azure_cloud/terragrunt/bi-platform"
        ]
        
        sensitive_files = [
            'sa_key.txt',
            'sa_name.txt', 
            'kubeconfig',
            'external_ip_traefik.txt',
            'dns_zone_complete_info.txt',
            'dns_zone_nameservers.txt'
        ]
        
        for base_dir in terraform_dirs_to_clean:
            if not os.path.exists(base_dir):
                continue
                
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file in sensitive_files:
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            logger.debug(f"Removed sensitive file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to remove sensitive file {file_path}: {str(e)}")
                            
    def _cleanup_temp_files(self):
        """Clean up temporary files created during deployment"""
        logger.info("Cleaning up temporary files...")
        
        temp_files = [
            f"/tmp/{self.customer}_infrastructure_deployment_files",
            f"/tmp/{self.customer}_customer_vault_structure.json",
            "infrastructure_deployment.log"
        ]
        
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    if os.path.isdir(temp_file):
                        shutil.rmtree(temp_file)
                    else:
                        os.remove(temp_file)
                    logger.debug(f"Removed temporary file/directory: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")
                    
    def _cleanup_secret_files(self):
        """Clean up secret files and sensitive configuration"""
        logger.info("Cleaning up secret files...")
        
        # Clean up any remaining secret files
        secret_patterns = [
            "*.key",
            "*.pem", 
            "*.crt",
            "*.p12",
            "*.pfx"
        ]
        
        terraform_dirs_to_clean = [
            "terraform/google_cloud/terragrunt",
            "terraform/aws_cloud/terragrunt",
            "terraform/azure_cloud/terragrunt"
        ]
        
        for base_dir in terraform_dirs_to_clean:
            if not os.path.exists(base_dir):
                continue
                
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    for pattern in secret_patterns:
                        if file.endswith(pattern.replace('*', '')):
                            file_path = os.path.join(root, file)
                            try:
                                os.remove(file_path)
                                logger.debug(f"Removed secret file: {file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove secret file {file_path}: {str(e)}")

    def _get_deployment_summary(self) -> Dict:
        """Get deployment summary"""
        summary = {
            "customer": self.customer,
            "cloud_provider": self.cloud_provider,
            "terraform_state": self.terraform_state,
            "git_provider": self.git_provider,
            "git_repo_url": self.git_repo_url,
            "method": self.method,
            "status": "success",
            "encryption_key": self.encryption_key  # Include encryption key in summary
        }
        logger.info("Deployment summary generated")
        return summary

    def _get_git_access_token_from_vault(self) -> str:
        """Get git access token from vault based on provider"""
        try:
            # Get vault path from environment or use default based on provider
            if self.git_provider == "github":
                vault_path = os.getenv('GITHUB_TOKEN_VAULT_PATH', '/data-platform-runner/ci-access-tokens/')
                secret_name = "GITHUB-TOKEN"
            elif self.git_provider == "gitlab":
                vault_path = os.getenv('GITLAB_TOKEN_VAULT_PATH', '/data-platform-runner/ci-access-tokens/')
                secret_name = "PRIVATE-TOKEN"
            elif self.git_provider == "bitbucket":
                vault_path = os.getenv('BITBUCKET_TOKEN_VAULT_PATH', '/data-platform-runner/ci-access-tokens/')
                secret_name = "BITBUCKET-TOKEN"
            elif self.git_provider == "gitea":
                vault_path = os.getenv('GITEA_TOKEN_VAULT_PATH', '/data-platform-runner/ci-access-tokens/')
                secret_name = "GITEA-TOKEN"
            else:
                # Default to GitLab for backward compatibility
                vault_path = os.getenv('GITLAB_TOKEN_VAULT_PATH', '/data-platform-runner/ci-access-tokens/')
                secret_name = "PRIVATE-TOKEN"
                
            logger.info(f"Attempting to retrieve {secret_name} from vault path: {vault_path}")
            token = self.vault_client.get_secret(
                secret_name=secret_name,
                secret_path=vault_path
            )
            logger.info(f"Successfully retrieved {self.git_provider} token from vault")
            return token
        except Exception as e:
            logger.error(f"Failed to get {self.git_provider} access token from vault: {str(e)}")
            raise ValueError(f"{self.git_provider.capitalize()} access token is required. Either provide it directly via --git_access_token parameter or ensure it exists in vault at the configured path")

class GitManager:
    """Handles Git operations with different authentication methods"""
    
    def __init__(self, repo_url: str, credentials: Dict, working_dir: str):
        self.repo_url = repo_url
        self.credentials = credentials
        self.working_dir = working_dir
        
    def clone_repository(self):
        """Clone repository with appropriate authentication"""
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir)
        
        if self.credentials.get('access_token'):
            # Use token-based authentication
            repo_url_with_token = self._add_token_to_url(self.repo_url, self.credentials['access_token'])
            self._git_clone(repo_url_with_token)
        elif self.credentials.get('private_key'):
            # Use SSH-based authentication
            self._setup_ssh_key()
            self._git_clone(self.repo_url)
        else:
            # Use basic authentication
            self._git_clone_with_basic_auth(self.repo_url, 
                                          self.credentials['username'],
                                          self.credentials['password'])
                                          
    def _add_token_to_url(self, url: str, token: str) -> str:
        """Add access token to repository URL"""
        if "https://" in url:
            # GitHub uses a different format: https://username:token@github.com/...
            # For GitHub, we'll use 'oauth2' as username for consistency
            return url.replace("https://", f"https://oauth2:{token}@")
        return url
        
    def _setup_ssh_key(self):
        """Setup SSH key for authentication"""
        ssh_dir = os.path.expanduser("~/.ssh")
        os.makedirs(ssh_dir, exist_ok=True)
        
        # Write private key
        with open(os.path.join(ssh_dir, "id_rsa"), "w") as f:
            f.write(self.credentials['private_key'])
            
        # Set permissions
        os.chmod(os.path.join(ssh_dir, "id_rsa"), 0o600)
        
    def _git_clone(self, repo_url: str):
        """Execute git clone command"""
        try:
            subprocess.run(['git', 'clone', repo_url, self.working_dir], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to clone repository: {e.stderr.decode()}")
            
    def _git_clone_with_basic_auth(self, repo_url: str, username: str, password: str):
        """Execute git clone with basic authentication"""
        try:
            # Create credentials file
            credentials_file = os.path.join(self.working_dir, ".git-credentials")
            with open(credentials_file, "w") as f:
                f.write(f"{repo_url}\n")
                
            # Configure git to use credentials
            subprocess.run(['git', 'config', '--global', 'credential.helper', 'store'], 
                         check=True, capture_output=True)
                         
            # Clone repository
            self._git_clone(repo_url)
            
        except Exception as e:
            raise GitError(f"Failed to clone repository with basic auth: {str(e)}")
            
    def commit_and_push(self, message: str):
        """Commit and push changes"""
        try:
            # Add all changes
            subprocess.run(['git', 'add', '.'], 
                         cwd=self.working_dir,
                         check=True, capture_output=True)
                         
            # Commit changes
            subprocess.run(['git', 'commit', '-m', message], 
                         cwd=self.working_dir,
                         check=True, capture_output=True)
                         
            # Push changes
            subprocess.run(['git', 'push'], 
                         cwd=self.working_dir,
                         check=True, capture_output=True)
                         
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to commit and push changes: {e.stderr.decode()}")

class ExternalInfisicalClient:
    """Client for external Infisical vault"""
    
    def __init__(self, project_id: str, client_id: str, client_secret: str):
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = os.getenv('FASTBI_VAULT_API_LINK', 'https://vault.fast.bi')
        
    def save_secret(self, secret_name: str, secret_value: str, secret_path: str) -> Dict:
        """Save secret to external vault"""
        try:
            # Authenticate
            access_token = self._authenticate()
            
            # Save secret
            url = f"{self.base_url}/api/v3/secrets/raw/{secret_name}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "workspaceId": self.project_id,
                "environment": "prod",
                "secretPath": secret_path,
                "secretValue": secret_value,
                "secretComment": "Encryption key for file encryption",
                "skipMultilineEncoding": True,
                "type": "shared"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to save secret to external vault: {str(e)}")
            raise

    def get_secret(self, secret_name: str, secret_path: str, access_token: Optional[str] = None, 
                  environment: str = "prod", version: Optional[str] = None, 
                  secret_type: str = "shared", include_imports: str = "false") -> str:
        """Retrieve the secret from the external Infisical vault."""
        try:
            if not access_token:
                access_token = self._authenticate()
                
            url = f"{self.base_url}/api/v3/secrets/raw/{secret_name}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "workspaceId": self.project_id,
                "environment": environment,
                "secretPath": secret_path,
                "version": version,
                "type": secret_type,
                "include_imports": include_imports
            }
            # Remove None values from params
            params = {k: v for k, v in params.items() if v is not None}
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()['secret']['secretValue']
            
        except Exception as e:
            logger.error(f"Failed to get secret from external vault: {str(e)}")
            raise

    def _authenticate(self) -> str:
        """Authenticate with external vault"""
        try:
            auth_url = f"{self.base_url}/api/v1/auth/universal-auth/login"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                "clientId": self.client_id,
                "clientSecret": self.client_secret
            }
            
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()['accessToken']
            
        except Exception as e:
            logger.error(f"Failed to authenticate with external vault: {str(e)}")
            raise

class LocalVaultClient:
    """Client for local vault"""
    
    def __init__(self, customer: str, kube_config: Optional[str], namespace: str):
        self.customer = customer
        self.kube_config = kube_config
        self.namespace = namespace
        self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
        self.port_forward_process = None
        self.vault_addr = "http://127.0.0.1:8200"
        
    def _setup_port_forward(self):
        """Setup port forward to vault"""
        try:
            cmd = [
                "kubectl", "port-forward", "vault-0", "-n", self.namespace,
                "8200:8200"
            ]
            
            if self.kube_config:
                cmd.extend(["--kubeconfig", self.kube_config])
                
            # Start port-forward in background
            self.port_forward_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for port-forward to be ready
            time.sleep(2)
            
        except Exception as e:
            if self.port_forward_process:
                self.port_forward_process.terminate()
            raise Exception(f"Failed to setup port forward: {str(e)}")
            
    def _cleanup_port_forward(self):
        """Cleanup port forward"""
        if self.port_forward_process:
            try:
                self.port_forward_process.terminate()
                self.port_forward_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.port_forward_process.kill()
            finally:
                self.port_forward_process = None

    def save_secret(self, secret_name: str, secret_value: str, secret_path: str) -> Dict:
        """Save secret to local vault using port-forwarding"""
        try:
            # Setup port forward
            self._setup_port_forward()
            
            # Get vault token from Kubernetes secret
            cmd = [
                "kubectl", "get", "secret", "vault-init", "-n", self.namespace,
                "-o", "jsonpath={.data.root-token}"
            ]
            if self.kube_config:
                cmd.extend(["--kubeconfig", self.kube_config])
                
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            root_token = base64.b64decode(result.stdout).decode('utf-8')
            
            # Save secret using vault API
            headers = {
                "X-Vault-Token": root_token,
                "Content-Type": "application/json"
            }
            
            # Create the secret path if it doesn't exist
            path = f"/v1/secret/data/{secret_path.lstrip('/')}/{secret_name}"
            payload = {
                "data": {
                    "value": secret_value
                }
            }
            
            response = requests.post(
                f"{self.vault_addr}{path}",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to save secret to local vault: {str(e)}")
            raise
        finally:
            self._cleanup_port_forward()

    def get_secret(self, secret_name: str, secret_path: str) -> str:
        """Retrieve the secret from the local vault JSON file."""
        try:
            logger.info(f"Attempting to get secret '{secret_name}' from path '{secret_path}' in file '{self.secret_file}'")
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")
                
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
                
            logger.info(f"Successfully retrieved secret '{secret_name}' from vault")
            return current[secret_name]
            
        except Exception as e:
            logger.error(f"Failed to get secret from local vault: {str(e)}")
            raise

def main():
    """Main entry point for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Infrastructure Deployment Operator")
    
    # Core arguments
    parser.add_argument('--customer', required=True, help='Customer name')
    parser.add_argument('--method', choices=['local_vault', 'external_infisical'], 
                       default='local_vault', help='Vault method')
    parser.add_argument('--cloud_provider', choices=['gcp', 'aws', 'azure', 'self-managed'],
                       required=True, help='Cloud provider')
    parser.add_argument('--terraform_state', choices=['local', 'remote'],
                       default='remote', help='Terraform state storage method')
    
    # Git configuration
    git_group = parser.add_argument_group('git configuration')
    git_group.add_argument('--git_repo_url', required=True, help='Git repository URL')
    git_group.add_argument('--git_provider', help='Git provider (auto-detected if not provided)')
    
    # Git authentication
    git_auth_group = parser.add_argument_group('git authentication')
    git_auth_group.add_argument('--git_access_token', help='Git access token')
    git_auth_group.add_argument('--git_private_key', help='Path to Git private key file')
    git_auth_group.add_argument('--git_username', help='Git username')
    git_auth_group.add_argument('--git_password', help='Git password')
    
    # Vault configuration
    vault_group = parser.add_argument_group('vault configuration')
    vault_group.add_argument('--vault_project_id', help='Vault project ID')
    vault_group.add_argument('--client_id', help='Secret manager client ID')
    vault_group.add_argument('--client_secret', help='Secret manager client secret')
    
    # Kubernetes configuration
    k8s_group = parser.add_argument_group('kubernetes configuration')
    k8s_group.add_argument('--kube_config_path', help='Path to kubeconfig file')
    k8s_group.add_argument('--namespace', default='vault', help='Kubernetes namespace')
    
    # Operation flags
    operation_group = parser.add_argument_group('operation flags')
    operation_group.add_argument('--force_deployment', action='store_true', 
                                help='Force deployment even if no infrastructure files are found')
    operation_group.add_argument('--no-cleanup', action='store_true',
                                help='Skip cleanup of local environment after deployment')
    
    args = parser.parse_args()
    
    try:
        # Initialize operator
        operator = InfrastructureDeploymentOperator(
            customer=args.customer,
            method=args.method,
            cloud_provider=args.cloud_provider,
            terraform_state=args.terraform_state,
            git_provider=args.git_provider,
            git_repo_url=args.git_repo_url,
            git_access_token=args.git_access_token,
            git_private_key=args.git_private_key,
            git_username=args.git_username,
            git_password=args.git_password,
            vault_project_id=args.vault_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            kube_config_path=args.kube_config_path,
            namespace=args.namespace,
            force_deployment=args.force_deployment,
            cleanup_enabled=not args.no_cleanup
        )
        
        # Collect and store infrastructure
        result = operator.collect_and_store_infrastructure()
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 