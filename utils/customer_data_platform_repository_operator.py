import os
import sys
import json
import logging
import argparse
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('customer_data_platform_repository_operator')

class CustomerDataPlatformRepositoryOperator:
    def __init__(self, 
                 customer: str,
                 domain: str,
                 method: str = "local_vault",
                 external_infisical_host: Optional[str] = None,
                 slug: Optional[str] = None,
                 vault_project_id: Optional[str] = None,
                 secret_manager_client_id: Optional[str] = None,
                 secret_manager_client_secret: Optional[str] = None,
                 git_provider: Optional[str] = None,
                 repo_authentication: str = "deploy_keys",
                 data_orchestrator_repo_url: Optional[str] = None,
                 data_model_repo_url: Optional[str] = None,
                 data_orchestrator_repo_private_key: Optional[str] = None,
                 data_model_repo_private_key: Optional[str] = None,
                 global_access_token: Optional[str] = None,
                 data_orchestrator_repo_access_token: Optional[str] = None,
                 data_model_repo_access_token: Optional[str] = None,
                 argo_server_url_type: str = "internal",
                 argo_cli_version: str = "v3.4.3",
                 cicd_workflows_template_version: str = "latest"):
        """Initialize the repository operator with configuration parameters."""
        
        self.customer = customer
        self.domain = domain
        self.method = method
        self.external_infisical_host = external_infisical_host
        self.slug = slug
        self.vault_project_id = vault_project_id
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.git_provider = git_provider
        self.repo_authentication = repo_authentication
        self.data_orchestrator_repo_url = data_orchestrator_repo_url
        self.data_model_repo_url = data_model_repo_url
        self.data_orchestrator_repo_private_key = data_orchestrator_repo_private_key
        self.data_model_repo_private_key = data_model_repo_private_key
        self.global_access_token = global_access_token
        self.data_orchestrator_repo_access_token = data_orchestrator_repo_access_token
        self.data_model_repo_access_token = data_model_repo_access_token
        
        # Initialize public key attributes (will be loaded from vault if needed)
        self.data_orchestrator_repo_public_key = None
        self.data_model_repo_public_key = None
        self.argo_server_url_type = argo_server_url_type if argo_server_url_type else "internal"
        self.argo_cli_version = argo_cli_version
        self.cicd_workflows_template_version = cicd_workflows_template_version

        # Validate method and required parameters
        if method not in ["local_vault", "external_infisical"]:
            raise ValueError(f"Unsupported method: {method}")

        # Validate method-specific requirements
        if method == "external_infisical":
            if not all([slug, vault_project_id, secret_manager_client_id, secret_manager_client_secret]):
                raise ValueError("slug, vault_project_id, secret_manager_client_id, and secret_manager_client_secret are required for external_infisical method")
        elif method == "local_vault":
            self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")

        # Set up temporary directory for repository operations
        self.temp_dir = tempfile.mkdtemp(prefix=f"{self.customer}_repos_")
        logger.info(f"Created temporary directory: {self.temp_dir}")

        # Load secrets if not provided
        self._load_secrets_if_needed()

    def __del__(self):
        """Cleanup temporary directory on object destruction."""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary directory: {e}")

    def _load_secrets_if_needed(self) -> None:
        """Load required secrets from vault if not provided."""
        try:
            access_token = self.authenticate_with_vault() if self.method == "external_infisical" else None

            # Load git provider if not provided
            if not self.git_provider:
                self.git_provider = self.get_secret_from_vault(
                    "GIT_PROVIDER", "/data-cicd-workflows/customer-cicd-variables/", access_token
                )
                if not self.git_provider:
                    self.git_provider = "gitlab"  # Default to gitlab if not found in vault
                logger.info(f"Using git provider from vault: {self.git_provider}")

            # Load repository URLs if not provided
            if not self.data_orchestrator_repo_url:
                self.data_orchestrator_repo_url = self.get_secret_from_vault(
                    "dag_repo_url", "/data-platform-runner/git_provider_repo_urls/", access_token
                )
            if not self.data_model_repo_url:
                self.data_model_repo_url = self.get_secret_from_vault(
                    "data_repo_url", "/data-platform-runner/git_provider_repo_urls/", access_token
                )

            # Load authentication credentials based on method
            if self.repo_authentication == "deploy_keys":
                if not self.data_orchestrator_repo_private_key:
                    self.data_orchestrator_repo_private_key = self.get_secret_from_vault(
                        "private", "/data-platform-runner/ssh-keys-data-orchestrator-repo/", access_token
                    )
                if not self.data_model_repo_private_key:
                    self.data_model_repo_private_key = self.get_secret_from_vault(
                        "private", "/data-platform-runner/ssh-keys-data-model-repo/", access_token
                    )
                
                # Validate that SSH keys were loaded
                if not self.data_orchestrator_repo_private_key:
                    raise ValueError("Failed to load orchestrator SSH private key from vault")
                if not self.data_model_repo_private_key:
                    raise ValueError("Failed to load data model SSH private key from vault")
                
                logger.info("SSH private keys loaded successfully from vault")
            else:  # access_token
                if not self.global_access_token:
                    self.global_access_token = self.get_secret_from_vault(
                        "PRIVATE-TOKEN", "/data-platform-runner/ci-access-tokens/", access_token
                    )
                if not self.data_orchestrator_repo_access_token:
                    self.data_orchestrator_repo_access_token = self.global_access_token
                if not self.data_model_repo_access_token:
                    self.data_model_repo_access_token = self.global_access_token
            
            # Load public keys for deploy keys
            if not self.data_model_repo_public_key:
                self.data_model_repo_public_key = self.get_secret_from_vault(
                    "public", "/data-platform-runner/ssh-keys-data-model-repo/", access_token
                )
            if not self.data_orchestrator_repo_public_key:
                self.data_orchestrator_repo_public_key = self.get_secret_from_vault(
                    "public", "/data-platform-runner/ssh-keys-data-orchestrator-repo/", access_token
                )

            # Display deploy keys information immediately after loading
            if self.repo_authentication == "deploy_keys" and self.data_orchestrator_repo_public_key and self.data_model_repo_public_key:
                logger.info("\n" + "="*80)
                logger.info("🔑 DEPLOY KEYS CONFIGURATION REQUIRED")
                logger.info("="*80)
                logger.info("")
                logger.info("You need to add the following deploy keys to your GitLab repositories:")
                logger.info("")
                
                # Data Orchestrator Repository
                logger.info("📁 DATA ORCHESTRATOR REPOSITORY:")
                logger.info(f"   Repository: {self.data_orchestrator_repo_url}")
                logger.info("   Deploy Key Title: Fast.BI Data Orchestrator Deploy Key")
                logger.info("   Public Key:")
                logger.info(f"   {self.data_orchestrator_repo_public_key}")
                logger.info("")
                
                # Data Model Repository
                logger.info("📁 DATA MODEL REPOSITORY:")
                logger.info(f"   Repository: {self.data_model_repo_url}")
                logger.info("   Deploy Key Title: Fast.BI Data Model Deploy Key")
                logger.info("   Public Key:")
                logger.info(f"   {self.data_model_repo_public_key}")
                logger.info("")
                
                logger.info("📋 INSTRUCTIONS:")
                logger.info("1. Go to each repository in GitLab")
                logger.info("2. Navigate to Settings > Repository > Deploy Keys")
                logger.info("3. Click 'Add deploy key'")
                logger.info("4. Enter the title and paste the corresponding public key")
                logger.info("5. Check 'Grant write permissions to this key' if needed")
                logger.info("6. Click 'Add key'")
                logger.info("")
                logger.info("="*80)
                logger.info("")

            # Create CI/CD Argo Server URL based on type
            if self.argo_server_url_type == "internal":
                self.argo_server_url = "data-platform-argo-workflows-server.cicd-workflows:2746"
            elif self.argo_server_url_type == "external":
                self.argo_server_url = f"https://workflows.{self.customer}.{self.domain}:443"
            else:
                raise ValueError(f"Invalid argo_server_url_type: {self.argo_server_url_type}")

        except Exception as e:
            logger.error(f"Failed to load secrets: {str(e)}")
            raise

    def _get_template_paths(self, repo_type: str) -> Dict[str, str]:
        """Get template paths for the given repository type."""
        base_path = "utils/templates/git_repo_templates"
        
        # Map fastbi to gitlab since fastbi is just a self-hosted GitLab instance
        git_provider = "gitlab" if self.git_provider == "fastbi" else self.git_provider
        
        paths = {
            'base': os.path.join(base_path, repo_type),
            'repository_structure': os.path.join(base_path, repo_type, "repository_structure"),
            'git_provider': os.path.join(base_path, repo_type, git_provider)
        }

        # Validate paths exist
        for path_type, path in paths.items():
            if not os.path.exists(path):
                if path_type == 'repository_structure':
                    raise FileNotFoundError(f"Required repository structure template not found: {path}")
                elif path_type == 'git_provider':
                    logger.warning(f"{path_type} template path not found: {path} - this is optional and will be skipped")
                else:
                    logger.warning(f"{path_type} template path not found: {path}")

        return paths

    def _copy_repository_structure(self, repo_type: str, work_dir: str) -> None:
        """Copy base repository structure from templates."""
        try:
            # Get template paths
            template_paths = self._get_template_paths(repo_type)
            repo_structure_dir = template_paths['repository_structure']

            logger.info(f"Copying repository structure from {repo_structure_dir} to {work_dir}")

            # Copy repository_structure directory as is
            if os.path.exists(repo_structure_dir):
                for item in os.listdir(repo_structure_dir):
                    src = os.path.join(repo_structure_dir, item)
                    dst = os.path.join(work_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
            else:
                logger.warning(f"Repository structure directory not found: {repo_structure_dir}")

            logger.info(f"Copied base repository structure for {repo_type}")

        except Exception as e:
            logger.error(f"Failed to copy repository structure: {str(e)}")
            raise

    def _setup_git_provider_files(self, work_dir: str, repo_type: str) -> None:
        """Set up git provider specific files with proper rendering."""
        try:
            # Get template paths
            template_paths = self._get_template_paths(repo_type)
            provider_dir = template_paths['git_provider']

            if not os.path.exists(provider_dir):
                logger.warning(f"Git provider directory not found: {provider_dir}")
                return

            logger.info(f"Setting up git provider files from {provider_dir}")

            # Recursively process all files in the provider directory
            template_files_found = 0
            for root, dirs, files in os.walk(provider_dir):
                # Calculate relative path from provider_dir
                rel_path = os.path.relpath(root, provider_dir)
                
                # Create corresponding directory in work_dir
                if rel_path != '.':
                    target_dir = os.path.join(work_dir, rel_path)
                    os.makedirs(target_dir, exist_ok=True)
                else:
                    target_dir = work_dir

                # Process files in current directory
                for file in files:
                    src_path = os.path.join(root, file)
                    
                    # Handle template files
                    if file.endswith('_template'):
                        template_files_found += 1
                        base_name = file[:-9]  # Remove '_template' suffix
                        dest_path = os.path.join(target_dir, base_name)
                        
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        
                        # Check if this is a hybrid template (contains both Jinja2 and GitHub Actions syntax)
                        with open(src_path, 'r') as f:
                            content = f.read()
                        
                        if '{{' in content and '{% raw %}' in content:
                            # This is a hybrid template - render Jinja2 first, then it becomes a GitHub Actions file
                            self._render_template_file(src_path, dest_path)
                            logger.info(f"Rendered hybrid template {src_path} to {dest_path} (Jinja2 + GitHub Actions)")
                        elif '${{ env.' in content and '{{' not in content:
                            # This is a pure GitHub Actions file, copy as-is without Jinja2 rendering
                            shutil.copy2(src_path, dest_path)
                            logger.info(f"Copied pure GitHub Actions template {src_path} to {dest_path} (no Jinja2 rendering)")
                        else:
                            # This is a regular Jinja2 template, render it
                            self._render_template_file(src_path, dest_path)
                            logger.info(f"Rendered Jinja2 template {src_path} to {dest_path}")
                    else:
                        # Copy non-template files as is
                        dest_path = os.path.join(target_dir, file)
                        shutil.copy2(src_path, dest_path)

            logger.info(f"Set up git provider specific files for {repo_type} - processed {template_files_found} template files")
            
            # Debug: List all files in the work directory
            logger.debug(f"Files in {work_dir} after template processing:")
            for root, dirs, files in os.walk(work_dir):
                rel_path = os.path.relpath(root, work_dir)
                if files:
                    logger.debug(f"  {rel_path}: {files}")

        except Exception as e:
            logger.error(f"Failed to set up git provider files: {str(e)}")
            raise

    def _render_template_file(self, template_path: str, output_path: str) -> None:
        """Render a template file with context."""
        try:
            # Prepare rendering context
            context = {
                'customer': self.customer,
                'git_provider': self.git_provider,
                'argo_server_url_type': self.argo_server_url_type,
                'ARGO_SERVER_URL': self.argo_server_url,
                'ARGO_CLI_VERSION': self.argo_cli_version,
                'CICD_WORKFLOWS_TEMPLATE_VERSION': self.cicd_workflows_template_version
            }

            # Create template environment
            env = Environment(
                loader=FileSystemLoader(os.path.dirname(template_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )

            # Render template
            template = env.get_template(os.path.basename(template_path))
            rendered_content = template.render(context)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Write rendered content
            with open(output_path, 'w') as f:
                f.write(rendered_content)

            logger.debug(f"Rendered template {template_path} to {output_path}")

        except Exception as e:
            logger.error(f"Failed to render template {template_path}: {str(e)}")
            raise

    def _setup_deploy_keys(self) -> None:
        """Set up SSH deploy keys for Git authentication."""
        try:
            logger.info("Setting up SSH deploy keys for Git authentication")
            
            # Validate SSH keys are present
            if not self.data_orchestrator_repo_private_key:
                raise ValueError("Orchestrator SSH private key not available")
            if not self.data_model_repo_private_key:
                raise ValueError("Data model SSH private key not available")
            
            # Create .ssh directory in the temporary directory
            ssh_dir = os.path.join(self.temp_dir, '.ssh')
            os.makedirs(ssh_dir, mode=0o700, exist_ok=True)

            # Write private keys to files
            orchestrator_key_path = os.path.join(ssh_dir, 'orchestrator_id_ed25519')
            data_model_key_path = os.path.join(ssh_dir, 'data_model_id_ed25519')

            with open(orchestrator_key_path, 'w') as f:
                f.write(self.data_orchestrator_repo_private_key)
            os.chmod(orchestrator_key_path, 0o600)

            with open(data_model_key_path, 'w') as f:
                f.write(self.data_model_repo_private_key)
            os.chmod(data_model_key_path, 0o600)

            # Create SSH config
            git_host = self._extract_git_host()
            
            # Use per-repository host aliases to ensure the right key is used
            config_content = f"""Host orchestrator
    HostName {git_host}
    User git
    IdentityFile {orchestrator_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    IdentitiesOnly yes

Host data_model
    HostName {git_host}
    User git
    IdentityFile {data_model_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    IdentitiesOnly yes
"""
            config_path = os.path.join(ssh_dir, 'config')
            with open(config_path, 'w') as f:
                f.write(config_content)
            os.chmod(config_path, 0o600)

            # Set environment variables for Git to use our SSH configuration
            os.environ['GIT_SSH_COMMAND'] = f'ssh -F {config_path}'
            os.environ['SSH_AUTH_SOCK'] = ''  # Disable SSH agent to force use of our keys
            
            logger.info(f"SSH configuration set up successfully in {ssh_dir}")

        except Exception as e:
            logger.error(f"Failed to set up deploy keys: {str(e)}")
            raise

    def _setup_access_token(self) -> None:
        """Set up Git access token authentication."""
        try:
            # Configure git to use the access tokens
            subprocess.run(['git', 'config', '--global', 'credential.helper', 'store'], check=True)
            credential_file = os.path.expanduser('~/.git-credentials')
            
            git_host = self._extract_git_host()
            
            # Write credentials for both repositories
            with open(credential_file, 'w') as f:
                if self.data_orchestrator_repo_access_token:
                    f.write(f"https://oauth2:{self.data_orchestrator_repo_access_token}@{git_host}\n")
                if self.data_model_repo_access_token and self.data_model_repo_access_token != self.data_orchestrator_repo_access_token:
                    f.write(f"https://oauth2:{self.data_model_repo_access_token}@{git_host}\n")
                elif self.global_access_token:
                    f.write(f"https://oauth2:{self.global_access_token}@{git_host}\n")
            
            os.chmod(credential_file, 0o600)

        except Exception as e:
            logger.error(f"Failed to set up access token: {str(e)}")
            raise

    def _extract_git_host(self) -> str:
        """Extract git host from repository URL."""
        url = self.data_orchestrator_repo_url or self.data_model_repo_url
        if not url:
            raise ValueError("No repository URL provided")
        
        if url.startswith('git@'):
            return url.split('@')[1].split(':')[0]
        elif url.startswith('http'):
            return url.split('/')[2]
        else:
            raise ValueError(f"Invalid repository URL format: {url}")

    def _render_repository_templates(self, repo_dir: str, repo_type: str) -> None:
        """Render repository templates with context."""
        try:
            context = {
                'customer': self.customer,
                'git_provider': self.git_provider,
                'argo_server_url_type': self.argo_server_url_type,
                'ARGO_SERVER_URL': self.argo_server_url,
                'ARGO_CLI_VERSION': self.argo_cli_version,
                'CICD_WORKFLOWS_TEMPLATE_VERSION': self.cicd_workflows_template_version
            }

            for root, _, files in os.walk(repo_dir):
                for file in files:
                    if file.endswith('_template'):
                        template_path = os.path.join(root, file)
                        output_path = template_path[:-9]  # Remove '_template' suffix
                        self._render_template_file(template_path, output_path)
                        os.remove(template_path)  # Remove template file after rendering

        except Exception as e:
            logger.error(f"Failed to render repository templates: {str(e)}")
            raise

    def authenticate_with_vault(self) -> Optional[str]:
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

    def get_secret_from_vault(self, secret_name: str, secret_path: str, access_token: Optional[str] = None) -> str:
        """Retrieve a secret from the vault using the appropriate method."""
        if self.method == "external_infisical":
            return self._get_secret_from_external_vault(secret_name, secret_path, access_token)
        else:
            return self._get_secret_from_local_vault(secret_name, secret_path)

    def _get_secret_from_external_vault(self, secret_name: str, secret_path: str, access_token: str) -> str:
        """Retrieve a secret from the external Infisical vault."""
        try:
            url = f"{self.external_infisical_host}/api/v3/secrets/raw/{secret_name}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {
                "workspaceId": self.vault_project_id,
                "environment": "prod",
                "secretPath": secret_path
            }
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()['secret']['secretValue']
        except Exception as e:
            logger.error(f"Failed to get secret from external vault: {str(e)}")
            raise

    def _get_secret_from_local_vault(self, secret_name: str, secret_path: str) -> str:
        """Retrieve a secret from the local vault JSON file."""
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

    def prepare_repository_structure(self, repo_type: str) -> None:
        """Prepare the repository structure based on the repository type."""
        try:
            # Determine repository URL and working directory
            repo_url = self.data_orchestrator_repo_url if repo_type == "data_orchestrator" else self.data_model_repo_url
            work_dir = os.path.join(self.temp_dir, f"{self.customer}_{repo_type}")
            
            if not repo_url:
                raise ValueError(f"Repository URL not provided for {repo_type}")

            # Check repository accessibility
            if not self._check_repository_accessibility(repo_url):
                raise ValueError(f"Repository {repo_url} is not accessible or does not exist")

            # Clone repository using appropriate authentication
            self._clone_repository(repo_url, work_dir, repo_type)

            # Copy base repository structure
            self._copy_repository_structure(repo_type, work_dir)

            # Render and copy git provider specific files
            self._setup_git_provider_files(work_dir, repo_type)

            # Commit and push changes
            self._commit_and_push_changes(work_dir, repo_type)

        except Exception as e:
            logger.error(f"Failed to prepare repository structure: {str(e)}")
            raise

    def _check_repository_accessibility(self, repo_url: str) -> bool:
        """Check if the repository is accessible and exists."""
        try:
            # Apply the same URL transformation logic as in _clone_repository
            check_url = repo_url
            
            if self.repo_authentication == "deploy_keys":
                # Convert HTTPS URL to SSH URL if needed
                if repo_url.startswith('https://'):
                    # Properly convert https://github.com/owner/repo.git to git@github.com:owner/repo.git
                    url_without_protocol = repo_url.replace('https://', '')
                    if '/' in url_without_protocol:
                        domain, path = url_without_protocol.split('/', 1)
                        check_url = f"git@{domain}:{path}"
            
            # For HTTPS URLs, try to access the repository
            if check_url.startswith('https://'):
                # Remove authentication tokens for the check
                clean_url = check_url
                if 'oauth2:' in clean_url:
                    clean_url = clean_url.replace('https://oauth2:', 'https://').split('@', 1)[1]
                
                # Try to access the repository using curl or requests
                import requests
                try:
                    response = requests.head(clean_url, timeout=10, allow_redirects=True)
                    if response.status_code in [200, 401, 403]:  # 401/403 means repo exists but needs auth
                        logger.info(f"Repository {clean_url} is accessible")
                        return True
                    elif response.status_code == 404:
                        logger.error(f"Repository {clean_url} not found (404)")
                        return False
                    else:
                        logger.warning(f"Repository {clean_url} returned status {response.status_code}")
                        return True  # Assume it exists if we get any response
                except requests.RequestException as e:
                    logger.warning(f"Could not check repository accessibility: {e}")
                    return True  # Assume it exists if we can't check
            
            # For SSH URLs, we can't easily check without SSH keys
            elif check_url.startswith('git@'):
                logger.info(f"SSH repository {check_url} - accessibility check skipped")
                return True
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking repository accessibility: {e}")
            return True  # Assume it exists if we can't check

    def _clone_repository(self, repo_url: str, work_dir: str, repo_type: str) -> None:
        """Clone repository using appropriate authentication method."""
        try:
            # Prepare repository URL based on authentication method
            if self.repo_authentication == "deploy_keys":
                # Convert HTTPS URL to SSH URL if needed
                if repo_url.startswith('https://'):
                    # Properly convert https://github.com/owner/repo.git to git@github.com:owner/repo.git
                    url_without_protocol = repo_url.replace('https://', '')
                    if '/' in url_without_protocol:
                        domain, path = url_without_protocol.split('/', 1)
                        repo_url = f"git@{domain}:{path}"
                
                # Force using per-repo host alias to ensure correct key selection
                alias = "orchestrator" if repo_type == "data_orchestrator" else "data_model"
                if repo_url.startswith('git@'):
                    # git@<host>:<path> -> git@<alias>:<path>
                    at_split = repo_url.split('@', 1)
                    host_and_path = at_split[1]
                    host, sep, path = host_and_path.partition(':')
                    clone_url = f"git@{alias}:{path}"
                else:
                    clone_url = repo_url
            else:
                # Use HTTPS URL with token
                if repo_url.startswith('git@'):
                    # Convert git@github.com:owner/repo.git to https://github.com/owner/repo.git
                    at_split = repo_url.split('@', 1)
                    host_and_path = at_split[1]
                    host, sep, path = host_and_path.partition(':')
                    repo_url = f"https://{host}/{path}"
                
                token = (self.data_orchestrator_repo_access_token 
                        if repo_type == "data_orchestrator" 
                        else self.data_model_repo_access_token) or self.global_access_token
                
                # For GitHub, use the token directly as username, for others use oauth2
                if 'github.com' in repo_url:
                    clone_url = repo_url.replace('https://', f'https://{token}@')
                else:
                    clone_url = repo_url.replace('https://', f'https://oauth2:{token}@')

            # Clone repository
            logger.info(f"Cloning {repo_type} repository to {work_dir}")
            
            try:
                subprocess.run(['git', 'clone', clone_url, work_dir], check=True)
                logger.info(f"Successfully cloned {repo_type} repository")
            except subprocess.CalledProcessError as e:
                # Check if the error is due to empty repository
                if "warning: You appear to have cloned an empty repository" in str(e.stderr) or "empty repository" in str(e.stderr):
                    logger.info(f"Repository is empty, initializing with default branch")
                    # Try to clone with --allow-empty-repository flag if available
                    try:
                        subprocess.run(['git', 'clone', '--allow-empty-repository', clone_url, work_dir], check=True)
                        logger.info(f"Successfully cloned empty repository")
                    except subprocess.CalledProcessError:
                        # Fallback: clone and initialize manually
                        subprocess.run(['git', 'clone', clone_url, work_dir], check=False)
                        # Initialize the repository manually
                        self._initialize_empty_repository(work_dir)
                else:
                    # Re-raise the original error if it's not about empty repository
                    raise

        except subprocess.CalledProcessError as e:
            # Check if the error is about repository not existing or access denied
            error_output = e.stderr.decode('utf-8') if e.stderr else str(e.stderr)
            if "could not be found" in error_output or "don't have permission" in error_output or "Permission denied" in error_output:
                logger.error(f"Repository access failed: {error_output}")
                logger.error("")
                logger.error("🔧 MANUAL ACTION REQUIRED:")
                logger.error(f"The repository {repo_url} either doesn't exist or you don't have access to it.")
                logger.error("")
                logger.error("Please check the following:")
                logger.error("1. Ensure the repository exists in your GitLab instance")
                logger.error("2. Verify you have access to the repository")
                logger.error("3. If using deploy keys, ensure the deploy key has been added to this repository")
                logger.error("4. Check the repository URL is correct")
                logger.error("")
                logger.error(f"Repository URL: {repo_url}")
                logger.error("")
                
                # Create a custom exception with helpful message
                raise Exception(f"Repository {repo_url} not accessible. Please ensure the repository exists and you have proper access permissions.")
            else:
                # Re-raise if it's a different error
                raise
        except Exception as e:
            logger.error(f"Error during repository cloning: {str(e)}")
            raise

    def _initialize_empty_repository(self, work_dir: str) -> None:
        """Initialize an empty repository with a default branch."""
        try:
            logger.info(f"Initializing empty repository in {work_dir}")
            
            # Initialize git repository
            subprocess.run(['git', 'init'], cwd=work_dir, check=True)
            
            # Add remote origin
            # Extract the original URL without authentication tokens
            original_url = self.data_orchestrator_repo_url if "data_orchestrator" in work_dir else self.data_model_repo_url
            if original_url.startswith('https://oauth2:'):
                # Remove the oauth2 token from URL
                original_url = original_url.replace('https://oauth2:', 'https://').split('@', 1)[1]
            
            subprocess.run(['git', 'remote', 'add', 'origin', original_url], cwd=work_dir, check=True)
            
            # Create initial commit with README
            readme_content = f"# {os.path.basename(work_dir)}\n\nInitial repository setup by Fast.BI Platform.\n"
            with open(os.path.join(work_dir, 'README.md'), 'w') as f:
                f.write(readme_content)
            
            # Add and commit the README
            subprocess.run(['git', 'add', 'README.md'], cwd=work_dir, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=work_dir, check=True)
            
            # Create and switch to main branch
            subprocess.run(['git', 'branch', '-M', 'main'], cwd=work_dir, check=True)
            
            logger.info(f"Successfully initialized empty repository with main branch")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize empty repository: {e}")
            raise
        except Exception as e:
            logger.error(f"Error initializing empty repository: {str(e)}")
            raise

    def _get_default_branch(self, repo_dir: str) -> str:
        """Get the default branch of the repository."""
        try:
            # Try to get the current branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            
            # Check if repository is empty (no commits)
            try:
                subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=repo_dir,
                    capture_output=True,
                    check=True
                )
                # If we get here, repository has commits
                return current_branch
            except subprocess.CalledProcessError:
                # Repository is empty, use 'main' as default
                logger.info("Repository is empty, using 'main' as default branch")
                return 'main'
                
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get default branch: {e}")
            return 'main'  # Default to 'main' if we can't determine

    def _commit_and_push_changes(self, work_dir: str, repo_type: str) -> None:
        """Commit and push changes to the repository."""
        try:
            # Configure git
            subprocess.run(['git', 'config', 'user.email', f"{self.customer}@fast.bi"], cwd=work_dir, check=True)
            subprocess.run(['git', 'config', 'user.name', f"FastBI Bot"], cwd=work_dir, check=True)

            # Get default branch
            default_branch = self._get_default_branch(work_dir)
            logger.info(f"Using branch: {default_branch}")

            # For empty repositories, we need to create the branch
            if default_branch == 'main':
                try:
                    # Try to create and checkout main branch
                    subprocess.run(['git', 'checkout', '-b', 'main'], cwd=work_dir, check=True)
                except subprocess.CalledProcessError:
                    # Branch might already exist
                    subprocess.run(['git', 'checkout', 'main'], cwd=work_dir, check=True)

            # Add all changes
            subprocess.run(['git', 'add', '.'], cwd=work_dir, check=True)

            # Check if there are any changes to commit
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=True
            )

            # Debug: Log git status output
            if status.stdout.strip():
                logger.info(f"Git status shows changes: {status.stdout.strip()}")
            else:
                logger.info("Git status shows no changes to commit")

            if status.stdout.strip():
                # Changes exist, commit them
                commit_message = f"Initial repository structure for {repo_type}"
                subprocess.run(['git', 'commit', '-m', commit_message], cwd=work_dir, check=True)

                # Try to push changes to the correct branch
                try:
                    # First, try to push with upstream tracking
                    subprocess.run(['git', 'push', '-u', 'origin', default_branch], cwd=work_dir, check=True)
                    logger.info(f"Successfully pushed changes to {repo_type} repository on branch {default_branch}")
                except subprocess.CalledProcessError as e:
                    # Check if the error is about default branch not existing or protected branch or permissions
                    error_output = e.stderr.decode('utf-8') if e.stderr else str(e.stderr)
                    if ("pre-receive hook declined" in error_output or "default branch" in error_output or
                        "protected branch" in error_output or "not permitted" in error_output or "You are not allowed to push" in error_output):
                        logger.error("Push failed due to remote permissions or default branch configuration.")
                        logger.error(f"Remote error:\n{error_output}")
                        logger.error("")
                        logger.error("🔧 MANUAL ACTION LIKELY REQUIRED:")
                        logger.error("- Ensure the deploy key has WRITE permissions on the repository")
                        logger.error("- Ensure the default branch is configured in GitLab (e.g., 'main' or 'master')")
                        logger.error("- Verify the branch is not protected against pushes")
                        logger.error("")
                        raise
                    else:
                        # Re-raise if it's a different error
                        raise
            else:
                # No changes to commit
                logger.info(f"No changes to commit for {repo_type} repository, structure is already up to date")

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.cmd}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr}")
            if e.stdout:
                logger.error(f"Command output: {e.stdout}")
            raise
        except Exception as e:
            logger.error(f"Failed to commit and push changes: {str(e)}")
            raise

    def run(self) -> Dict[str, Any]:
        """Main execution method to set up both repositories."""
        try:
            logger.info(f"Starting repository setup for customer: {self.customer}")

            # Set up Git credentials based on authentication method
            if self.repo_authentication == "deploy_keys":
                self._setup_deploy_keys()
            elif self.repo_authentication == "access_token":
                self._setup_access_token()
            else:
                raise ValueError(f"Unsupported authentication method: {self.repo_authentication}")

            # Process data orchestrator repository
            logger.info("Setting up data orchestrator repository")
            self.prepare_repository_structure("data_orchestrator")

            # Process dbt data model repository
            logger.info("Setting up dbt data model repository")
            self.prepare_repository_structure("dbt_data_model")

            # Add information about required secret variables
            logger.info("\nIMPORTANT: For the dbt data model repository, you need to add the following secret variables:")
            logger.info("1. CI_ACCESS_TOKEN_NAME - GitLab access token name")
            logger.info("2. CI_ACCESS_TOKEN - GitLab access token value")
            logger.info("3. ARGO_WORKFLOW_SA_TOKEN - Argo workflow service account token")
            logger.info("These secrets will be provided during the platform deployment process.")

            return {
                "status": "success",
                "message": "Successfully set up both repositories. Please note that the dbt data model repository requires additional secret variables to be configured. As well as the deploy keys for the repositories.",
                "customer": self.customer,
                "repositories": {
                    "data_orchestrator": self.data_orchestrator_repo_url,
                    "dbt_data_model": self.data_model_repo_url
                },
                "required_secrets": {
                    "dbt_data_model": [
                        "CI_ACCESS_TOKEN_NAME",
                        "CI_ACCESS_TOKEN",
                        "ARGO_WORKFLOW_SA_TOKEN"
                    ]
                },
                "required_ssh_deploy_keys": {
                    "dbt_data_model": {
                        "public_key": self.data_model_repo_public_key,
                        "key_title": "Deploy Key for dbt_data_model repository"
                    },
                    "data_orchestrator": {
                        "public_key": self.data_orchestrator_repo_public_key,
                        "key_title": "Deploy Key for data_orchestrator repository"
                    }
                }
            }

        except Exception as e:
            logger.error(f"Repository setup failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "customer": self.customer
            }

    @classmethod
    def from_cli_args(cls, args):
        """Create an instance from CLI arguments."""
        return cls(
            customer=args.customer,
            domain=args.domain,
            method=args.method,
            external_infisical_host=args.external_infisical_host,
            slug=args.slug,
            vault_project_id=args.vault_project_id,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            git_provider=args.git_provider,
            repo_authentication=args.repo_authentication,
            data_orchestrator_repo_url=args.data_orchestrator_repo_url,
            data_model_repo_url=args.data_model_repo_url,
            data_orchestrator_repo_private_key=args.data_orchestrator_repo_private_key,
            data_model_repo_private_key=args.data_model_repo_private_key,
            global_access_token=args.global_access_token,
            data_orchestrator_repo_access_token=args.data_orchestrator_repo_access_token,
            data_model_repo_access_token=args.data_model_repo_access_token,
            argo_server_url_type=args.argo_server_url_type,
            argo_cli_version=args.argo_cli_version,
            cicd_workflows_template_version=args.cicd_workflows_template_version
        )

def main():
    parser = argparse.ArgumentParser(
        description="Customer Data Platform Repository Operator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    required_args = parser.add_argument_group('required arguments')
    required_args.add_argument(
        '--customer',
        required=True,
        help='Customer name'
    )
    required_args.add_argument(
        '--domain',
        required=True,
        help='Domain name (e.g., fast.bi)'
    )
    required_args.add_argument(
        '--argo_server_url_type',
        choices=['internal', 'external'],
        required=True,
        help='Argo server URL type (internal: data-platform-argo-workflows-server.cicd-workflows:2746, external: https://workflows.<customer>.<domain>:443)'
    )

    # Optional arguments with defaults
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--method',
        choices=['external_infisical', 'local_vault'],
        default='local_vault',
        help='Vault method to use (default: local_vault)'
    )
    optional_args.add_argument(
        '--repo_authentication',
        choices=['deploy_keys', 'access_token'],
        default='deploy_keys',
        help='Repository authentication method (default: deploy_keys)'
    )
    optional_args.add_argument(
        '--git_provider',
        choices=['gitlab', 'github', 'bitbucket', 'gitea'],
        help='Git provider (default: from vault or gitlab)'
    )

    # Advanced configuration (all optional)
    advanced_args = parser.add_argument_group('advanced configuration (optional)')
    advanced_args.add_argument(
        '--external_infisical_host',
        help='External Infisical host URL'
    )
    advanced_args.add_argument(
        '--slug',
        help='Project slug for vault'
    )
    advanced_args.add_argument(
        '--vault_project_id',
        help='Vault project ID'
    )
    advanced_args.add_argument(
        '--client_id',
        help='Secret manager client ID'
    )
    advanced_args.add_argument(
        '--client_secret',
        help='Secret manager client secret'
    )
    advanced_args.add_argument(
        '--data_orchestrator_repo_url',
        help='Data orchestrator repository URL'
    )
    advanced_args.add_argument(
        '--data_model_repo_url',
        help='Data model repository URL'
    )
    advanced_args.add_argument(
        '--data_orchestrator_repo_private_key',
        help='Private key for data orchestrator repository'
    )
    advanced_args.add_argument(
        '--data_model_repo_private_key',
        help='Private key for data model repository'
    )
    advanced_args.add_argument(
        '--global_access_token',
        help='Global access token for all repositories'
    )
    advanced_args.add_argument(
        '--data_orchestrator_repo_access_token',
        help='Access token for data orchestrator repository'
    )
    advanced_args.add_argument(
        '--data_model_repo_access_token',
        help='Access token for data model repository'
    )
    advanced_args.add_argument(
        '--argo_cli_version',
        default='v3.4.3',
        help='Argo CLI version'
    )
    advanced_args.add_argument(
        '--cicd_workflows_template_version',
        default='latest',
        help='CI/CD workflows template version'
    )

    # Debug option
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        operator = CustomerDataPlatformRepositoryOperator.from_cli_args(args)
        result = operator.run()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "success" else 1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    main()
