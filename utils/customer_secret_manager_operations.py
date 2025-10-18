import os
import sys
import requests
import random
import string
import subprocess
import json
import base64
import secrets
from jinja2 import Environment, FileSystemLoader
from secrets import choice as secrets_choice
from cryptography.fernet import Fernet
import logging
import time
import argparse
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Get the rate limit from environment variable, default to 50 if not set
VAULT_API_MAX_REQUEST = int(os.getenv('VAULT_API_MAX_REQUEST', 50))

class CustomerSecretManagerError(Exception):
    """Base exception class for CustomerSecretManager errors"""
    pass

class ValidationError(CustomerSecretManagerError):
    """Raised when input validation fails"""
    pass

class AuthenticationError(CustomerSecretManagerError):
    """Raised when authentication fails"""
    pass

class APIError(CustomerSecretManagerError):
    """Raised when API calls fail"""
    pass

class SingletonBase:
    _instances = {}
    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cls] = instance
        return cls._instances[cls]

class CustomerSecretManager(SingletonBase):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = logging.getLogger(__name__)
            try:
                self._initialize_parameters(**kwargs)
                self._initialize_optional_parameters(kwargs)
                self._setup_api_endpoints()
                self._initialize_caches()
                self._setup_authentication()
                self._setup_repositories()
                self._setup_cloud_provider()
                self._setup_data_warehouse()
                self.logger.info("CustomerSecretManager initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize CustomerSecretManager: {str(e)}", exc_info=True)
                raise

    def _initialize_parameters(self, **kwargs):
        """Initialize all class parameters with proper error handling"""
        try:
            self.client_id = kwargs.get('client_id')
            self.client_secret = kwargs.get('client_secret')
            self.user_email = kwargs.get('user_email')
            self.method = kwargs.get('method')
            self.customer = kwargs.get('customer')
            self.domain_name = kwargs.get('domain_name')
            self.data_analysis_platform = kwargs.get('data_analysis_platform')
            self.data_warehouse_platform = kwargs.get('data_warehouse_platform')
            self.git_provider = kwargs.get('git_provider')
            self.dag_repo_url = kwargs.get('dag_repo_url')
            self.data_repo_url = kwargs.get('data_repo_url')
            self.data_repo_main_branch = kwargs.get('data_repo_main_branch', 'master')
            self.repo_method = kwargs.get('repo_access_method', 'access_token')
            self.git_provider_access_token = kwargs.get('git_provider_access_token')
            self.project_id = kwargs.get('project_id')
            self.region = kwargs.get('project_region')
            self.aws_region = kwargs.get('aws_region')
            self.aws_access_key_id = kwargs.get('aws_access_key_id')
            self.aws_secret_access_key = kwargs.get('aws_secret_access_key')
            self.cloud_provider = kwargs.get('cloud_provider')
            self.orchestrator_platform = kwargs.get('orchestrator_platform', 'Airflow')
            self.default_git_user_email = f"{self.customer}@{self.domain_name}"
            self.bigquery_project_id = kwargs.get('bigquery_project_id')
            self.bigquery_region = kwargs.get('bigquery_region')

            # Process service account JSONs if provided and data warehouse is BigQuery
            if self.data_warehouse_platform == 'bigquery':
                if kwargs.get('data_platform_sa_json'):
                    sa_json = self._decode_and_parse_sa_json(kwargs['data_platform_sa_json'])
                    if sa_json:
                        self.data_platform_gcp_sa_email = sa_json.get('client_email')
                        self.data_platform_gcp_sa_secret = kwargs['data_platform_sa_json']
                    else:
                        logger.warning("Failed to decode/parse data platform service account JSON")

                if kwargs.get('data_analysis_sa_json'):
                    sa_json = self._decode_and_parse_sa_json(kwargs['data_analysis_sa_json'])
                    if sa_json:
                        self.data_analysis_gcp_sa_email = sa_json.get('client_email')
                        self.data_analysis_gcp_sa_secret = kwargs['data_analysis_sa_json']
                    else:
                        logger.warning("Failed to decode/parse data analysis service account JSON")

            # Initialize all optional parameters
            self._initialize_optional_parameters(kwargs)
            
        except Exception as e:
            logger.error(f"Failed to initialize parameters: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Parameter initialization failed: {str(e)}")

    def _decode_and_parse_sa_json(self, sa_json_str):
        """Decode and parse service account JSON from base64 string."""
        try:
            if self._is_base64(sa_json_str):
                decoded_json = base64.b64decode(sa_json_str).decode('utf-8')
                return json.loads(decoded_json)
            else:
                return json.loads(sa_json_str)
        except Exception as e:
            logger.error(f"Failed to decode/parse service account JSON: {str(e)}", exc_info=True)
            return None

    def _initialize_optional_parameters(self, kwargs):
        """Initialize all optional parameters"""
        optional_params = {
            'private_key_orchestrator': None,
            'public_key_orchestrator': None,
            'private_key_data_model': None,
            'public_key_data_model': None,
            'smtp_host': None,
            'smtp_port': None,
            'smtp_username': None,
            'smtp_password': None,
            'lookersdk_base_url': None,
            'lookersdk_client_id': None,
            'lookersdk_client_secret': None,
            'data_platform_sa_json': None,
            'data_analysis_sa_json': None,
            'bigquery_project_id': None,
            'bigquery_region': None,
            'aws_access_key_id': None,
            'aws_secret_access_key': None,
            'aws_region': None,
            'azure_client_id': None,
            'azure_client_secret': None,
            'runner_registration_token': None,
            'redshift_host': None,
            'redshift_database': None,
            'redshift_port': None,
            'redshift_user': None,
            'redshift_password': None,
            'snowflake_account': None,
            'snowflake_user': None,
            'snowflake_password': None,
            'snowflake_warehouse': None,
            'snowflake_database': None,
            'snowflake_private_key': None,
            'snowflake_public_key': None,
            'snowflake_passphrase': None,
            'fabric_server': None,
            'fabric_database': None,
            'fabric_port': None,
            'fabric_user': None,
            'fabric_password': None,
            'fabric_authentication': None,
            'data_analysis_gcp_sa_email': None,
            'data_analysis_gcp_sa_secret': None,
            'data_platform_gcp_sa_email': None,
            'data_platform_gcp_sa_secret': None
        }
        
        for param, default in optional_params.items():
            setattr(self, param, kwargs.get(param, default))

        # Process service account JSONs if provided and data warehouse is BigQuery
        if self.data_warehouse_platform == 'bigquery' and kwargs.get('data_platform_sa_json'):
            try:
                sa_json = self._decode_and_parse_sa_json(kwargs['data_platform_sa_json'])
                if sa_json and sa_json.get('client_email'):
                    self.data_platform_gcp_sa_email = sa_json['client_email']
                    self.data_platform_gcp_sa_secret = kwargs['data_platform_sa_json']
            except Exception as e:
                logger.warning(f"Failed to process data platform service account JSON: {str(e)}")

        if self.data_warehouse_platform == 'bigquery' and kwargs.get('data_analysis_sa_json'):
            try:
                sa_json = self._decode_and_parse_sa_json(kwargs['data_analysis_sa_json'])
                if sa_json and sa_json.get('client_email'):
                    self.data_analysis_gcp_sa_email = sa_json['client_email']
                    self.data_analysis_gcp_sa_secret = kwargs['data_analysis_sa_json']
            except Exception as e:
                logger.warning(f"Failed to process data analysis service account JSON: {str(e)}")

    def _setup_api_endpoints(self):
        """Setup API endpoints with proper error handling"""
        try:
            self.url_base = os.getenv('FASTBI_VAULT_API_LINK', 'https://vault.fast.bi')
            self.org_id = os.getenv('FASTBI_VAULT_ORG_ID', '90e27461-3806-4e98-90ec-9f2b496cd5bc')
            self.url_base_api_v1 = f"{self.url_base}/api/v1"
            self.url_base_api_v2 = f"{self.url_base}/api/v2"
            self.url_base_api_v3 = f"{self.url_base}/api/v3"
        except Exception as e:
            logger.error(f"Failed to setup API endpoints: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"API endpoint setup failed: {str(e)}")

    def _initialize_caches(self):
        """Initialize caches and counters"""
        self.env_cache = {}
        self.secrets_cache = {}
        self.last_request_time = 0
        self.request_count = 0

    def _setup_authentication(self):
        """Setup authentication parameters"""
        if self.method == 'external_infisical' and not (self.client_id and self.client_secret):
            logger.warning("External Infisical method selected but client credentials not provided")

    def _setup_repositories(self):
        """Setup repository URLs and access methods"""
        try:
            self.dag_repo_push_url = self.create_repo_push_url(self.dag_repo_url, self.git_provider_access_token, self.customer)
            self.data_repo_push_url = self.create_repo_push_url(self.data_repo_url, self.git_provider_access_token, self.customer)
        except Exception as e:
            logger.error(f"Failed to setup repositories: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Repository setup failed: {str(e)}")

    def _setup_cloud_provider(self):
        """Setup cloud provider specific configurations"""
        if self.cloud_provider == 'gcp':
            if not (self.project_id and self.region):
                logger.warning("GCP cloud provider selected but project_id or region not provided")
        elif self.cloud_provider == 'aws':
            if not (self.aws_access_key_id and self.aws_secret_access_key and self.aws_region):
                logger.warning("AWS cloud provider selected but credentials not provided")
        elif self.cloud_provider == 'azure':
            if not (self.azure_client_id and self.azure_client_secret):
                logger.warning("Azure cloud provider selected but credentials not provided")

    def _setup_data_warehouse(self):
        """Setup data warehouse specific configurations"""
        if self.data_warehouse_platform == 'bigquery':
            if not (self.bigquery_project_id and self.bigquery_region):
                logger.warning("BigQuery selected but project_id or region not provided")
        elif self.data_warehouse_platform == 'redshift':
            if not all([self.redshift_host, self.redshift_database, self.redshift_port, 
                       self.redshift_user, self.redshift_password]):
                logger.warning("Redshift selected but some required parameters are missing")
        elif self.data_warehouse_platform == 'snowflake':
            if not all([self.snowflake_account, self.snowflake_user, self.snowflake_warehouse, 
                       self.snowflake_database]):
                logger.warning("Snowflake selected but some required parameters are missing")
        elif self.data_warehouse_platform == 'fabric':
            if not all([self.fabric_server, self.fabric_database, self.fabric_port, 
                       self.fabric_user, self.fabric_password, self.fabric_authentication]):
                logger.warning("MS Fabric selected but some required parameters are missing")

    def rate_limit(self):
        """Implement rate limiting with proper error handling"""
        try:
            current_time = time.time()
            if current_time - self.last_request_time >= 60:
                self.last_request_time = current_time
                self.request_count = 0
            
            if self.request_count >= VAULT_API_MAX_REQUEST:
                sleep_time = 60 - (current_time - self.last_request_time)
                if sleep_time > 0:
                    logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
                    time.sleep(sleep_time)
                self.last_request_time = time.time()
                self.request_count = 0
            
            self.request_count += 1
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            raise APIError(f"Rate limiting failed: {str(e)}")

    def authenticate_with_infisical(self):
        """Authenticate with Infisical with proper error handling"""
        try:
            auth_url = f"{self.url_base_api_v1}/auth/universal-auth/login"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {'clientId': self.client_id, 'clientSecret': self.client_secret}
            
            self.rate_limit()
            response = requests.post(auth_url, headers=headers, data=data)
            
            if response.status_code == 200:
                return response.json()['accessToken']
            else:
                logger.error(f"Authentication failed: {response.text}")
                raise AuthenticationError(f"Authentication failed: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during authentication: {str(e)}", exc_info=True)
            raise APIError(f"Network error during authentication: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}", exc_info=True)
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    def create_repo_push_url(self, repo_url, git_provider_access_token, customer):
        # Check the repository method and construct the URL accordingly
        if self.repo_method == 'access_token':
            # Convert SSH URL to HTTPS if needed
            if repo_url.startswith('git@'):
                # Convert git@github.com:owner/repo.git to https://github.com/owner/repo.git
                at_split = repo_url.split('@', 1)
                host_and_path = at_split[1]
                host, sep, path = host_and_path.partition(':')
                repo_url = f"https://{host}/{path}"
            
            # Ensure the repo_url has https:// protocol
            if not repo_url.startswith("https://"):
                repo_url = f"https://{repo_url}"
            
            # For GitHub, use the token directly as username, for others use oauth2
            if 'github.com' in repo_url:
                return repo_url.replace('https://', f'https://{git_provider_access_token}@')
            else:
                return repo_url.replace('https://', f'https://oauth2:{git_provider_access_token}@')
                
        elif self.repo_method == 'deploy_keys':
            # Convert HTTPS URL to SSH URL if needed
            if repo_url.startswith('https://'):
                # Properly convert https://github.com/owner/repo.git to git@github.com:owner/repo.git
                url_without_protocol = repo_url.replace('https://', '')
                if '/' in url_without_protocol:
                    domain, path = url_without_protocol.split('/', 1)
                    return f"git@{domain}:{path}"
            
            # If already in SSH format, fix any malformed URLs
            if repo_url.startswith('git@'):
                # Fix incorrect SSH URLs that use / instead of : after the domain
                # Pattern: git@domain/path -> git@domain:path
                if 'git@' in repo_url and '/' in repo_url:
                    # Split at the first / after git@
                    git_part, rest = repo_url.split('/', 1)
                    if ':' not in git_part:  # Only fix if : is not already present
                        return f"{git_part}:{rest}"
                return repo_url
            
            # Fallback: assume it's a domain and add git@ prefix
            return f"git@{repo_url}"
        else:
            raise ValueError("Invalid repository method. Supported values are 'access_token' and 'deploy_keys'.")

    def retriew_secret_from_terragrunt_output(self, cloud_provider, model_catalog):
        project_root = os.getcwd()  # assuming this method is run at project root
        sa_key_file = os.path.join(project_root, 'terraform', cloud_provider, 'terragrunt', 'bi-platform', model_catalog, 'sa_key.txt')
        sa_name_file = os.path.join(project_root, 'terraform', cloud_provider, 'terragrunt', 'bi-platform', model_catalog, 'sa_name.txt')

        with open(sa_key_file, 'r') as file:
            sa_key_content = file.read()
            sa_key_based64 = sa_key_content
            sa_key_decoded = base64.b64decode(sa_key_content)
            sa_key_json = json.loads(sa_key_decoded)

        with open(sa_name_file, 'r') as file:
            sa_name_content = file.read()
            prefix = '/serviceAccounts/'
            start_index = sa_name_content.find(prefix) + len(prefix)
            if start_index > len(prefix) - 1:  # Ensure prefix was found
                sa_name = sa_name_content[start_index:]
            else:
                raise ValueError("Service account name format is incorrect.")

        return sa_key_based64, sa_key_json, sa_name

    def random_string(self, length=3):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def create_project_identity(self, identity_name, org_id, access_token):
        """Create project identity with proper error handling"""
        try:
            full_identity_name = f"{self.customer}-{identity_name}"
            url = f"{self.url_base_api_v1}/identities"
            payload = {
                "name": full_identity_name,
                "organizationId": org_id,
                "role": "no-access"
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            self.rate_limit()
            response = requests.post(url, json=payload, headers=headers)
            
            if 200 <= response.status_code < 300:
                try:
                    identity_id = response.json().get('identity', {}).get('id')
                    if identity_id:
                        logger.info(f"Created project identity: {full_identity_name} with ID: {identity_id}")
                        return identity_id, full_identity_name
                    else:
                        logger.error("Identity ID not found in response")
                        raise APIError("Identity ID not found in response")
                except (KeyError, ValueError) as e:
                    logger.error(f"Error parsing identity creation response: {str(e)}", exc_info=True)
                    raise APIError(f"Error parsing identity creation response: {str(e)}")
            else:
                logger.error(f"Identity creation failed: {response.status_code} {response.text}")
                raise APIError(f"Identity creation failed: {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during identity creation: {str(e)}", exc_info=True)
            raise APIError(f"Network error during identity creation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during identity creation: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Identity creation failed: {str(e)}")

    def attach_universal_auth_to_identity(self, identity_id, access_token):
        """Attach universal auth to identity with proper error handling"""
        try:
            url = f"{self.url_base_api_v1}/auth/universal-auth/identities/{identity_id}"
            payload = {
                "clientSecretTrustedIps": [{"ipAddress": "0.0.0.0/0"}],
                "accessTokenTrustedIps": [{"ipAddress": "0.0.0.0/0"}],
                "accessTokenTTL": 2592000,
                "accessTokenMaxTTL": 2592000,
                "accessTokenNumUsesLimit": 0
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }

            self.rate_limit()
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                try:
                    client_id = response.json().get('identityUniversalAuth', {}).get('clientId')
                    if client_id:
                        logger.info(f"Attached universal auth to identity {identity_id}")
                        return client_id
                    else:
                        logger.error("Client ID not found in response")
                        raise APIError("Client ID not found in response")
                except (KeyError, ValueError) as e:
                    logger.error(f"Error parsing universal auth response: {str(e)}", exc_info=True)
                    raise APIError(f"Error parsing universal auth response: {str(e)}")
            else:
                logger.error(f"Attaching universal auth failed: {response.status_code} {response.text}")
                raise APIError(f"Attaching universal auth failed: {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during universal auth attachment: {str(e)}", exc_info=True)
            raise APIError(f"Network error during universal auth attachment: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during universal auth attachment: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Universal auth attachment failed: {str(e)}")

    def create_project_identity_secret(self, identity_id, access_token, description):
        """Create project identity secret with proper error handling"""
        try:
            url = f"{self.url_base_api_v1}/auth/universal-auth/identities/{identity_id}/client-secrets"
            payload = {
                "description": description,
                "numUsesLimit": 0,
                "ttl": 0
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            self.rate_limit()
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                client_secret = response.json().get('clientSecret')
                if client_secret:
                    logger.info(f"Created project identity secret for identity {identity_id}")
                    return client_secret
                else:
                    logger.error("Client secret not found in response")
                    raise APIError("Client secret not found in response")
            else:
                logger.error(f"Error creating project identity secret: {response.text}")
                raise APIError(f"Error creating project identity secret: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during secret creation: {str(e)}", exc_info=True)
            raise APIError(f"Network error during secret creation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during secret creation: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Secret creation failed: {str(e)}")

    def create_workspace(self, access_token):
        """Create workspace with proper error handling"""
        try:
            slug = f"{self.customer}-{self.random_string(3)}-{random.randint(10,99)}"
            workspace_api_endpoint = f"{self.url_base_api_v2}/workspace"
            payload = {"projectName": self.customer, "slug": slug}
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            self.rate_limit()
            response = requests.post(workspace_api_endpoint, json=payload, headers=headers)
            
            if response.status_code == 200:
                try:
                    project_id = response.json()['project']['id']
                    environments = {env['slug']: env['id'] for env in response.json()['project']['environments']}
                    slug = response.json()['project']['slug']
                    logger.info(f"Created workspace with Project Slug: {slug} and Project ID: {project_id}")
                    return project_id, environments, slug
                except (KeyError, ValueError) as e:
                    logger.error(f"Error parsing workspace creation response: {str(e)}", exc_info=True)
                    raise APIError(f"Error parsing workspace creation response: {str(e)}")
            else:
                logger.error(f"Workspace creation failed: {response.text}")
                raise APIError(f"Workspace creation failed: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during workspace creation: {str(e)}", exc_info=True)
            raise APIError(f"Network error during workspace creation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during workspace creation: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Workspace creation failed: {str(e)}")

    def add_user_to_workspace(self, project_id, access_token, user_email):
        """Add user to workspace with proper error handling"""
        try:
            url = f"{self.url_base_api_v2}/workspace/{project_id}/memberships"
            payload = {"emails": [user_email]}
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            self.rate_limit()
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                membership_id = response.json().get('memberships', [{}])[0].get('id')
                if membership_id:
                    logger.info(f"Added user {user_email} to workspace {project_id}")
                    return membership_id
                else:
                    logger.error("Membership ID not found in response")
                    raise APIError("Membership ID not found in response")
            else:
                logger.error(f"Error adding user to workspace: {response.text}")
                raise APIError(f"Error adding user to workspace: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during user addition: {str(e)}", exc_info=True)
            raise APIError(f"Network error during user addition: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during user addition: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"User addition failed: {str(e)}")

    def add_sa_to_workspace(self, project_id, access_token, sa_id, role):
        """Add service account to workspace with proper error handling"""
        try:
            url = f"{self.url_base_api_v2}/workspace/{project_id}/identity-memberships/{sa_id}"
            payload = {"role": role}
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            self.rate_limit()
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                membership_id = response.json().get('identityMembership', {}).get('id')
                if membership_id:
                    logger.info(f"Added service account {sa_id} to workspace {project_id} with role {role}")
                    return membership_id
                else:
                    logger.error("Identity membership ID not found in response")
                    raise APIError("Identity membership ID not found in response")
            else:
                logger.error(f"Error adding service account to workspace: {response.text}")
                raise APIError(f"Error adding service account to workspace: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during service account addition: {str(e)}", exc_info=True)
            raise APIError(f"Network error during service account addition: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during service account addition: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Service account addition failed: {str(e)}")

    def update_user_role(self, workspace_id, membership_id, access_token, role):
        url = f"{self.url_base_api_v1}/workspace/{workspace_id}/memberships/{membership_id}"
        payload = {"roles": [{"isTemporary": False, "role": role}]}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        response = requests.patch(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to update user role: {response.text}")

    def update_the_project_del_environment(self, workspace_id, access_token, env_id):
        url = f"{self.url_base_api_v1}/workspace/{workspace_id}/environments/{env_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        response = requests.delete(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to delete project environment: {response.text}")

    def update_the_project_add_folder(self, workspace_id, access_token, folder_structure, parent_path="/"):
        created_folders = []
        url = f"{self.url_base_api_v1}/folders"
        for folder_name, contents in folder_structure.items():
            current_path = f"{parent_path.rstrip('/')}/{folder_name}/"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            if isinstance(contents, dict) and any(isinstance(v, dict) for v in contents.values()):
                payload = {
                    "workspaceId": workspace_id,
                    "environment": "prod",
                    "name": folder_name,
                    "path": parent_path.rstrip('/')
                }
                self.rate_limit()
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    subfolders = self.update_the_project_add_folder(workspace_id, access_token, contents, current_path)
                    created_folders.extend(subfolders)
                else:
                    logger.error(f"Failed to add folder '{current_path}': {response.status_code} {response.text}")
            elif isinstance(contents, dict):
                payload = {
                    "workspaceId": workspace_id,
                    "environment": "prod",
                    "name": folder_name,
                    "path": parent_path.rstrip('/')
                }
                self.rate_limit()
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    created_folders.append(current_path)
                else:
                    logger.error(f"Failed to add secrets folder '{current_path}': {response.status_code} {response.text}")
        return created_folders

    def import_secrets(self, workspace_id, access_token, path, secret_key, secret_value):
        created_secrets = []
        
        # Convert secret_value to string and handle special cases
        if secret_value is None or secret_value == "":
            secret_value = "EMPTY"
        else:
            # Convert any non-string value to string
            secret_value = str(secret_value)

        # Handle reference values
        if secret_value.startswith("ref:"):
            ref_path = secret_value[4:]
            if ref_path in self.secrets_cache:
                secret_value = str(self.secrets_cache[ref_path])
            else:
                logger.warning(f"Reference '{ref_path}' not found in cache. Secret creation aborted.")
                return created_secrets

        url = f"{self.url_base_api_v3}/secrets/raw/{secret_key}"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "workspaceId": workspace_id,
            "environment": "prod",
            "secretPath": f"/{path}",
            "secretValue": secret_value,  # Now guaranteed to be a string
            "secretComment": "",
            "skipMultilineEncoding": True,
            "type": "shared"
        }

        self.rate_limit()
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            created_secrets.append(f"Secret '{secret_key}' created successfully in '{path}'.")
            self.secrets_cache[path + secret_key] = secret_value
        else:
            logger.error(f"Failed to import Secret '{secret_key}' in path '{path}': {response.status_code} {response.text}")

        return created_secrets

    def resolve_secret_reference(self, ref_path):
        """Resolve a secret reference to its actual value."""
        # First attempt to retrieve the secret from cache
        if ref_path in self.secrets_cache:
            return self.secrets_cache[ref_path]
        
        # Special case for local vault method during initial file creation
        if self.method == 'local_vault' and not hasattr(self, '_processing_references'):
            # Return the reference as is for now, we'll resolve it in post-processing
            return f"ref:{ref_path}"
        
        # Fetch the secret from storage if not in cache
        secret_value = self.fetch_secret_by_path(ref_path)
        if secret_value:
            self.secrets_cache[ref_path] = secret_value
        
        return secret_value

    def parse_and_import_secrets(self, structure, workspace_id, access_token, path=''):
        all_created_secrets = []  # Collect all messages from secret creation attempts

        if not isinstance(structure, dict):
            raise ValueError(f"Expected a dictionary but got {type(structure).__name__}: {structure}")

        for key, value in structure.items():
            current_path = f"{path}{key}/" if path else f"{key}/"
            if isinstance(value, dict) and all(isinstance(v, str) or v is None for v in value.values()):  # This is a secrets directory
                for secret_key, secret_value in value.items():
                    # Handle special cases or generate new secrets
                    if secret_value == "random":
                        secret_value = self.generate_secure_password()
                    elif secret_value == "fernet_random":
                        secret_value = self.generate_fernet_key()
                    elif secret_value == "private_key_orchestrator":
                        secret_value = self.private_key_orchestrator if self.private_key_orchestrator is not None else self.export_private_key(agent_name="fast_bi_orchestrator_agent")
                    elif secret_value == "public_key_orchestrator":
                        secret_value = self.public_key_orchestrator if self.public_key_orchestrator is not None else self.export_public_key(agent_name="fast_bi_orchestrator_agent")
                    elif secret_value == "private_key_data_model":
                        secret_value = self.private_key_data_model if self.private_key_data_model is not None else self.export_private_key(agent_name="fast_bi_data_model_agent")
                    elif secret_value == "public_key_data_model":
                        secret_value = self.public_key_data_model if self.public_key_data_model is not None else self.export_public_key(agent_name="fast_bi_data_model_agent")
                    elif secret_value == "data_repo_url":
                        secret_value = self.data_repo_url if self.data_repo_url is not None else 'EMPTY'
                    elif secret_value == "dag_repo_url":
                        secret_value = self.dag_repo_url if self.dag_repo_url is not None else 'EMPTY'
                    elif secret_value == "git_provider_access_token":
                        secret_value = self.git_provider_access_token if self.git_provider_access_token is not None else 'EMPTY'
                    elif secret_value == "git_provider_access_token_name":
                        secret_value = f"{self.customer}_fastbi_agent_access_token"
                    elif secret_value == "data_analysis_gcp_sa_email":
                        secret_value = self.data_analysis_gcp_sa_email if self.data_analysis_gcp_sa_email is not None else 'EMPTY'
                    elif secret_value == "data_analysis_gcp_sa_secret":
                        secret_value = self.data_analysis_gcp_sa_secret if self.data_analysis_gcp_sa_secret is not None else 'EMPTY'
                    elif secret_value == "data_platform_gcp_sa_email":
                        secret_value = self.data_platform_gcp_sa_email if self.data_platform_gcp_sa_email is not None else 'EMPTY'
                    elif secret_value == "data_platform_gcp_sa_secret":
                        secret_value = self.data_platform_gcp_sa_secret if self.data_platform_gcp_sa_secret is not None else 'EMPTY'
                    elif secret_value == "random_10":
                        secret_value = self.generate_secure_password(length=10)
                    elif secret_value == "bigquery_project_id":
                        secret_value = self.bigquery_project_id if self.bigquery_project_id is not None else 'EMPTY'
                    elif secret_value == "bigquery_region":
                        secret_value = self.bigquery_region if self.bigquery_region is not None else 'EMPTY'
                    elif secret_value == "redshift_host":
                        secret_value = self.redshift_host if self.redshift_host is not None else 'EMPTY'
                    elif secret_value == "redshift_database":
                        secret_value = self.redshift_database if self.redshift_database is not None else 'EMPTY'
                    elif secret_value == "redshift_user":
                        secret_value = self.redshift_user if self.redshift_user is not None else 'EMPTY'
                    elif secret_value == "redshift_password":
                        secret_value = self.redshift_password if self.redshift_password is not None else 'EMPTY'
                    elif secret_value == "snowflake_account":
                        secret_value = self.snowflake_account if self.snowflake_account is not None else 'EMPTY'
                    elif secret_value == "snowflake_user":
                        secret_value = self.snowflake_user if self.snowflake_user is not None else 'EMPTY'
                    elif secret_value == "snowflake_password":
                        secret_value = self.snowflake_password if self.snowflake_password is not None else 'EMPTY'
                    elif secret_value == "snowflake_warehouse":
                        secret_value = self.snowflake_warehouse if self.snowflake_warehouse is not None else 'EMPTY'
                    elif secret_value == "snowflake_database":
                        secret_value = self.snowflake_database if self.snowflake_database is not None else 'EMPTY'
                    elif secret_value == "snowflake_private_key":
                        if not hasattr(self, 'snowflake_private_key') or self.snowflake_private_key in [None, 'EMPTY']:
                            self.logger.info("Generating Snowflake key pair")
                            private_key, public_key, passphrase = self.generate_snowflake_keys()
                            self.snowflake_private_key = private_key
                            self.snowflake_public_key = public_key
                            self.snowflake_passphrase = passphrase
                        secret_value = self.snowflake_private_key
                    elif secret_value == "snowflake_public_key":
                        if not hasattr(self, 'snowflake_public_key') or self.snowflake_public_key in [None, 'EMPTY']:
                            self.logger.info("Generating Snowflake key pair")
                            private_key, public_key, passphrase = self.generate_snowflake_keys()
                            self.snowflake_private_key = private_key
                            self.snowflake_public_key = public_key
                            self.snowflake_passphrase = passphrase
                        secret_value = self.snowflake_public_key
                    elif secret_value == "snowflake_passphrase":
                        if not hasattr(self, 'snowflake_passphrase') or self.snowflake_passphrase in [None, 'EMPTY']:
                            self.logger.info("Generating Snowflake key pair")
                            private_key, public_key, passphrase = self.generate_snowflake_keys()
                            self.snowflake_private_key = private_key
                            self.snowflake_public_key = public_key
                            self.snowflake_passphrase = passphrase
                        secret_value = self.snowflake_passphrase
                    elif secret_value == "fabric_server":
                        secret_value = self.fabric_server if self.fabric_server is not None else 'EMPTY'
                    elif secret_value == "fabric_database":
                        secret_value = self.fabric_database if self.fabric_database is not None else 'EMPTY'
                    elif secret_value == "fabric_user":
                        secret_value = self.fabric_user if self.fabric_user is not None else 'EMPTY'
                    elif secret_value == "fabric_password":
                        secret_value = self.fabric_password if self.fabric_password is not None else 'EMPTY'
                    elif secret_value == "fabric_authentication":
                        secret_value = "activeDirectory"
                    elif secret_value == "airflow_conn_aws":
                        access_key_path = "data-platform-storage/root-buckets-secrets/airflow-fast-bi-bucket-admin/CONSOLE_ACCESS_KEY"
                        secret_key_path = "data-platform-storage/root-buckets-secrets/airflow-fast-bi-bucket-admin/CONSOLE_SECRET_KEY"
                        airflow_access_key = self.resolve_secret_reference(access_key_path)
                        aiflow_secret_key = self.resolve_secret_reference(secret_key_path)
                        secret_value = f"aws://{airflow_access_key}:{aiflow_secret_key}@/?endpoint_url=http%3A%2F%2Fminio.minio.svc.cluster.local"
                    elif secret_value == "smtp_host":
                        secret_value = self.smtp_host
                    elif secret_value == "smtp_port":
                        secret_value = f"{self.smtp_port}"
                    elif secret_value == "smtp_username":
                        secret_value = self.smtp_username
                    elif secret_value == "smtp_password":
                        secret_value = self.smtp_password
                    elif secret_value == "datahub_neo4j_credentials":
                        datahub_neo4j_username_path = "data-governance/neo4j-secrets/username"
                        datahub_neo4j_password_path = "data-governance/neo4j-secrets/password"
                        datahub_neo4j_username = self.resolve_secret_reference(datahub_neo4j_username_path)
                        datahub_neo4j_password = self.resolve_secret_reference(datahub_neo4j_password_path)
                        secret_value = f"{datahub_neo4j_username}/{datahub_neo4j_password}"
                    elif secret_value == "customer":
                        secret_value = self.customer
                    elif secret_value == "domain":
                        secret_value = self.domain_name
                    elif secret_value == "project_id":
                        secret_value = self.project_id
                    elif secret_value == "region":
                        secret_value = self.region
                    elif secret_value == "aws_region":
                        secret_value = self.aws_region
                    elif secret_value == "aws_access_key_id":
                        secret_value = self.aws_access_key_id
                    elif secret_value == "aws_secret_access_key":
                        secret_value = self.aws_secret_access_key
                    elif secret_value == "dag_repo_push":
                        secret_value = self.dag_repo_push_url
                    elif secret_value == "data_analysis_platform":
                        secret_value = self.data_analysis_platform
                    elif secret_value == "data_warehouse_platform":
                        secret_value = self.data_warehouse_platform
                    elif secret_value == "data_repo_main_branch":
                        secret_value = self.data_repo_main_branch
                    elif secret_value == "git_provider":
                        secret_value = self.git_provider
                    elif secret_value == "data_repo_url":
                        secret_value = self.data_repo_url
                    elif secret_value == "default_git_user_email":
                        secret_value = self.default_git_user_email
                    elif secret_value == "orchestrator_platform":
                        secret_value = self.orchestrator_platform
                    elif secret_value == "access_token_name":
                        secret_value = f"{self.customer}_agent_access_token"
                    elif secret_value == "lookersdk_base_url":
                        secret_value = self.lookersdk_base_url
                    elif secret_value == "lookersdk_client_id":
                        secret_value = self.lookersdk_client_id
                    elif secret_value == "lookersdk_client_secret":
                        secret_value = self.lookersdk_client_secret
                    elif secret_value == "cookie_random":
                        secret_value = self.generate_hexadecimal_password()
                    elif secret_value == "runner_registration_token":
                        secret_value = self.runner_registration_token

                    created_secrets = self.import_secrets(workspace_id, access_token, current_path, secret_key, secret_value)
                    all_created_secrets.extend(created_secrets)
            else:  # Recurse into subdirectories
                subdirectory_secrets = self.parse_and_import_secrets(value, workspace_id, access_token, current_path)
                all_created_secrets.extend(subdirectory_secrets)
        return all_created_secrets

    def execute_command(self, command):
        """
        Executes a given command through the shell, printing the output or errors directly.
        
        Args:
        - command (str): The command to execute.
        """
        try:
            # Execute the command, capture output, and check for errors automatically
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            
            # If the command was successful, print the output
            print("Command executed successfully.")
            print("Output:", result.stdout)
        except subprocess.CalledProcessError as e:
            # If the command fails, print the error
            print("Error executing command:")
            print(e.stderr)

    def render_template(self, template_path, output_path, context):
        """
        Renders a template with the given context and writes the output to a file.

        Args:
        - template_path (str): Path to the Jinja2 template file.
        - output_path (str): Path to write the rendered output.
        - context (dict): A dictionary of values to render the template with.
        """
        # Load the template environment and template file
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))
        
        # Render the template with the provided context
        output = template.render(context)
        
        # Write the rendered output to the specified file
        with open(output_path, 'w') as f:
            f.write(output)

    def generate_secure_password(self, length=32):
        """Generate a secure random password of a specified length, using only alphanumeric characters."""
        alphabet = string.ascii_letters + string.digits  # Use only letters and digits
        password = ''.join(secrets_choice(alphabet) for _ in range(length))
        return password
    
    def generate_strong_secure_password(self, length=32):
        """Generate a strong Base64 Encoded secure random password of a specified length, using only alphanumeric characters."""
        # Calculate the required length of the raw password to get the desired length after Base64 encoding
        raw_length = (length * 3) // 4
        password = self.generate_secure_password(raw_length)
        # Encode the password and decode it to get a string
        encoded_password = base64.b64encode(password.encode()).decode()
        # Ensure the encoded password meets the length requirement, trim if necessary
        return encoded_password[:length]
    
    def generate_fernet_key(self):
        """Generate a URL-safe base64-encoded 32-byte key suitable for Fernet encryption."""
        key = Fernet.generate_key()
        return key.decode()

    def generate_hexadecimal_password(self, length=32):
        """Generate a secure random hexadecimal password of a specified even length."""
        if length % 2 != 0:
            raise ValueError("Length must be an even number to ensure full bytes are represented.")
        # Generate a random hexadecimal string
        password = secrets.token_hex(length // 2)  # Divide by 2 because each byte is two hex digits
        return password

    def generate_ssh_keys(self, comment, key_name):
        """Generate SSH keys for Git operations.
        
        Args:
            comment (str): Comment to add to the key
            key_name (str): Name of the key file
            
        Returns:
            Tuple[str, str]: Private and public keys
        """
        try:
            logger.info(f"Generating SSH keys with comment: {comment}")
            # Run ssh-keygen and redirect output to /dev/null
            subprocess.run([
                "ssh-keygen", "-t", "ed25519", "-C", comment, "-f", key_name, "-N", ""
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.debug("SSH keys generated, reading files")
            with open(f"{key_name}", "r") as file:
                private_key = file.read()
            with open(f"{key_name}.pub", "r") as file:
                public_key = file.read()
            
            logger.debug("Cleaning up temporary key files")
            # Clean up files
            os.remove(key_name)
            os.remove(f"{key_name}.pub")
            
            logger.info("SSH key pair generated successfully")
            return private_key, public_key
        except subprocess.CalledProcessError as e:
            logger.error(f"Error generating SSH keys: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_ssh_keys: {e}", exc_info=True)
            raise

    def generate_snowflake_keys(self):
        """Generate Snowflake key pair and passphrase following Snowflake's documentation."""
        try:
            # Generate a secure passphrase
            passphrase = self.generate_secure_password(32)
            
            # Create temporary files for key generation
            private_key_path = "/tmp/snowflake_private_key.p8"
            public_key_path = "/tmp/snowflake_public_key.pub"
            
            # Generate private key using OpenSSL
            private_key_cmd = f"openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 des3 -inform PEM -out {private_key_path} -passout pass:{passphrase}"
            self.execute_command(private_key_cmd)
            
            # Generate public key from private key
            public_key_cmd = f"openssl rsa -in {private_key_path} -pubout -out {public_key_path} -passin pass:{passphrase}"
            self.execute_command(public_key_cmd)
            
            # Read the generated keys
            with open(private_key_path, 'r') as f:
                private_key = f.read().strip()
            with open(public_key_path, 'r') as f:
                public_key = f.read().strip()
            
            # Clean up temporary files
            self.execute_command(f"rm {private_key_path} {public_key_path}")
            
            self.logger.info("Snowflake key pair generated successfully")
            return private_key, public_key, passphrase
            
        except Exception as e:
            self.logger.error(f"Failed to generate Snowflake keys: {str(e)}", exc_info=True)
            raise CustomerSecretManagerError(f"Failed to generate Snowflake keys: {str(e)}")

    def export_private_key(self, agent_name):
        key_name = f"{agent_name}_private_key"  # Create a unique key name based on the agent
        if key_name not in self.secrets_cache:
            private_key, public_key = self.generate_ssh_keys(comment=agent_name, key_name=key_name)
            self.secrets_cache[key_name] = private_key
            self.secrets_cache[f"{agent_name}_public_key"] = public_key
        return self.secrets_cache[key_name]

    def export_public_key(self, agent_name):
        key_name = f"{agent_name}_public_key"  # Create a unique key name based on the agent
        if key_name not in self.secrets_cache:
            self.export_private_key(agent_name)  # This will populate both private and public keys
        return self.secrets_cache[key_name]
    
    def manage_kubernetes_integration(self, sa_client_id, sa_client_secret, slug):
        command_universal_credentials = f"kubectl create secret generic universal-auth-credentials --from-literal=clientId=\"{sa_client_id}\" --from-literal=clientSecret=\"{sa_client_secret}\" --namespace=infisical-operator-system"
        self.execute_command(command_universal_credentials)
        
        # Template rendering and kubectl application
        context = {'project_slug': slug}
        template_path = 'charts/infra_services_charts/sercret_manager_operator/infisical-secret-crd-identity.yaml'
        rendered_yaml_path = 'infisical-secret-crd-identity-rendered.yaml'
        self.render_template(template_path, rendered_yaml_path, context)
        
        command_apply_crd = f"kubectl apply -f {rendered_yaml_path} --namespace=infisical-operator-system"
        self.execute_command(command_apply_crd)
        os.remove(rendered_yaml_path)
        logger.info(f"Successfully applied the CRD and removed the temporary file: {rendered_yaml_path}")

    def fetch_secret_by_path(self, path):
        """
        Fetch a secret value by its path.
        
        Args:
        - path (str): The path to the secret, e.g., "data-platform-storage/root-buckets-secrets/access-key"
        
        Returns:
        - str: The secret value
        """
        # First check if we already have it in cache
        if path in self.secrets_cache:
            return self.secrets_cache[path]
        
        # For local_vault method, we need to handle refs differently since we're building the structure
        if self.method == 'local_vault':
            # For local vault during initialization, return a placeholder
            # This will be replaced later when actually creating the secrets
            logger.warning(f"Reference to path '{path}' not found in cache during local vault initialization.")
            return f"REF_TO_{path}"
        
        # For Infisical, try to fetch from the API
        if self.method == 'external_infisical':
            # Split the path into components
            components = path.split('/')
            if len(components) < 2:
                raise ValueError(f"Invalid path format: {path}. Expected format: 'folder/secret_key'")
                
            # The last component is the key, the rest is the path
            secret_key = components[-1]
            secret_path = '/'.join(components[:-1])
            
            url = f"{self.url_base_api_v3}/secrets/raw/{secret_key}"
            headers = {"Authorization": f"Bearer {self._current_access_token}", "Content-Type": "application/json"}
            params = {
                "workspaceId": self._current_workspace_id,
                "environment": "prod",
                "secretPath": f"/{secret_path}"
            }
            
            self.rate_limit()
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                secret_value = response.json().get('secret', {}).get('secretValue')
                # Cache the value for future use
                self.secrets_cache[path] = secret_value
                return secret_value
            else:
                logger.error(f"Failed to fetch secret at path '{path}': {response.status_code} {response.text}")
                return None
        
        # Default fallback - return None if the path wasn't found
        logger.warning(f"No method available to fetch secret at path '{path}'")
        return None

    def create_temp_file(self, temp_file_path):
        """Create a temporary file from the secrets template and fill it with values."""
        # Load the secrets template
        template_file_path = 'utils/templates/secret_structure_template/customer_vault_structure.json'
        with open(template_file_path, 'r') as template_file:
            template_data = json.load(template_file)
        
        # Create a structure to hold our filled values
        output_structure = {}
        
        # Temporarily replace import_secrets with our file-writing version
        original_import_secrets = self.import_secrets
        self.import_secrets = lambda workspace_id, access_token, path, secret_key, secret_value: self._collect_secret_for_file(output_structure, path, secret_key, secret_value)
        
        try:
            # Run the existing parse_and_import_secrets function with our temporary replacement
            self.parse_and_import_secrets(template_data, workspace_id="dummy", access_token="dummy")
            
            # Write the filled structure to the file
            with open(temp_file_path, 'w') as temp_file:
                json.dump(output_structure, temp_file, indent=4)
            
            return output_structure
        finally:
            # Restore the original function
            self.import_secrets = original_import_secrets

    def _collect_secret_for_file(self, structure, path, secret_key, secret_value):
        """Helper function that collects secrets into a structure instead of making API calls."""
        result = []
        
        # Handle None/empty values
        if secret_value is None or secret_value == "":
            secret_value = "EMPTY"
        
        # Resolve references
        if isinstance(secret_value, str) and secret_value.startswith("ref:"):
            ref_path = secret_value[4:]
            if ref_path in self.secrets_cache:
                secret_value = self.secrets_cache[ref_path]
            else:
                # Try to get from our structure
                parts = ref_path.split('/')
                current = structure
                found = True
                
                for part in parts[:-1]:
                    if part in current:
                        current = current[part]
                    else:
                        found = False
                        break
                
                if found and parts[-1] in current:
                    secret_value = current[parts[-1]]
                else:
                    result.append(f"Reference '{ref_path}' not found in cache. Using placeholder.")
                    # Keep the reference as is for now
        
        # Add to our secrets cache
        full_path = path.rstrip('/') + '/' + secret_key
        self.secrets_cache[full_path] = secret_value
        
        # Build path in the structure
        path_parts = [p for p in path.strip('/').split('/') if p]
        current = structure
        
        for part in path_parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Add the secret
        current[secret_key] = secret_value
        result.append(f"Collected '{secret_key}' for file structure at path '{path}'")
        
        return result

    def run(self):
        messages = []  # List to collect operation messages
        response_data = {}  # Dictionary to hold response data
        try:
            if self.method == 'external_infisical':
                # Logic for Infisical Vault (external)
                messages.append("Using external Infisical Vault method.")

                access_token = self.authenticate_with_infisical()
                messages.append("Authenticated successfully.")

                # Create project identity and manage authentication and roles
                identity_id, full_identity_name = self.create_project_identity("secret-manager-agent", self.org_id, access_token)
                sa_client_id = self.attach_universal_auth_to_identity(identity_id, access_token)
                sa_client_secret = self.create_project_identity_secret(identity_id, access_token, f"Secret Manager Agent for {full_identity_name}")
                messages.append(f"Identity {full_identity_name} created with ID {identity_id}.")

                # Create workspace and manage users and environments
                project_id, environments, slug = self.create_workspace(access_token)
                messages.append(f"Workspace created with Project Slug: {slug} and Project ID: {project_id}.")

                membership_id_fastbi_administrator = self.add_user_to_workspace(project_id, access_token, 'administrator@fast.bi')
                if membership_id_fastbi_administrator:
                    self.update_user_role(project_id, membership_id_fastbi_administrator, access_token, "admin")
                    messages.append("Main fast.bi Administrator added to workspace with admin role.")
                membership_id = self.add_user_to_workspace(project_id, access_token, self.user_email)
                if membership_id:
                    self.update_user_role(project_id, membership_id, access_token, "admin")
                    self.add_sa_to_workspace(project_id, access_token, identity_id, "member")
                    messages.append(f"User {self.user_email} added to workspace with admin role.")

                # To delete specific environments.
                environments2delete = ["dev", "staging"]
                for env_slug in environments2delete:
                    env_id = environments.get(env_slug)
                    if env_id:
                        self.update_the_project_del_environment(project_id, access_token, env_id)
                    else:
                        logger.info(f"Environment slug '{env_slug}' not found in project.")

                # Creating folder structure in project
                folder_structure_file = 'utils/templates/secret_structure_template/customer_vault_structure.json'
                with open(folder_structure_file, 'r') as file:
                    folder_structure = json.load(file)
                folders_created = self.update_the_project_add_folder(project_id, access_token, folder_structure)

                # Import Secrets in Infisical New Project
                secrets_created = self.parse_and_import_secrets(folder_structure, workspace_id=project_id, access_token=access_token)

                # Optionally manage Kubernetes secrets and CRD
                if os.getenv('K8S_DEPLOYMENT', 'False') == 'True':
                    self.manage_kubernetes_integration(sa_client_id, sa_client_secret, slug)

                response_data.update({
                    'project_id': project_id,
                    'slug': slug,
                    'sa_id': identity_id,
                    'client_id': sa_client_id,
                    'client_secret': sa_client_secret,
                    'folders_created': folders_created,
                    'secrets_created': secrets_created,
                    'status': "success"
                })
                return response_data

            elif self.method == 'local_vault':
                # Logic for HashiCorp Vault (local)
                messages.append("Using local HashiCorp Vault method.")

                # Step 1: Create a temporary file from the secrets template
                temp_file_path = f"/tmp/{self.customer}_customer_vault_structure.json"
                self.create_temp_file(temp_file_path)
                messages.append(f"Temporary secrets file created at {temp_file_path}")

                messages.append("Secrets pushed to local HashiCorp Vault successfully.")
                
                response_data.update({
                    'temp_file_path': temp_file_path,
                    'status': "success"
                })

            else:
                raise ValueError("Invalid method specified. Supported values are 'external_infisical' and 'local_vault'.")
                
            response_data['status'] = "success"
            response_data['messages'] = messages
            return response_data

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return {"error": str(e)}, 500  # Return a structured error response

    @staticmethod
    def _is_base64(s):
        """Check if a string is base64 encoded."""
        try:
            if not isinstance(s, str):
                return False
            # Check if the string contains only valid base64 characters
            if not all(c in string.ascii_letters + string.digits + '+/=' for c in s):
                return False
            # Try to decode
            base64.b64decode(s)
            return True
        except Exception:
            return False

    @classmethod
    def validate_inputs(cls, **kwargs):
        errors = []
        method = kwargs.get('method')
        data_warehouse_platform = kwargs.get('data_warehouse_platform')
        cloud_provider = kwargs.get('cloud_provider')

        # Method validation
        if method not in ['external_infisical', 'local_vault']:
            errors.append("method must be either 'external_infisical' or 'local_vault'")
        
        # External Infisical specific requirements
        if method == 'external_infisical':
            if not kwargs.get('client_id'):
                errors.append("client_id is required for external_infisical method")
            if not kwargs.get('client_secret'):
                errors.append("client_secret is required for external_infisical method")
        
        # Required fields regardless of method
        required_fields = {
            'customer': 'Customer name',
            'user_email': 'User email',
            'data_analysis_platform': 'Data analysis platform',
            'data_warehouse_platform': 'Data warehouse platform',
            'git_provider': 'Git provider',
            'dag_repo_url': 'DAG repository URL',
            'data_repo_url': 'Data repository URL'
        }
        
        for field, description in required_fields.items():
            if not kwargs.get(field):
                errors.append(f"{description} is required")

        # Cloud Provider Validation
        if cloud_provider:
            if cloud_provider not in ['gcp', 'aws', 'azure', 'self-managed']:
                errors.append("cloud_provider must be one of: gcp, aws, azure, self-managed")

            # GCP specific validation
            if cloud_provider == 'gcp':
                if not kwargs.get('project_id'):
                    errors.append("project_id is required when cloud_provider is gcp")
                if not kwargs.get('project_region'):
                    errors.append("project_region is required when cloud_provider is gcp")
                
                project_id = kwargs.get('project_id')
                if project_id and not re.match(r'^[a-z][-a-z0-9]{4,28}[a-z0-9]$', project_id):
                    errors.append("GCP project_id must be 6-30 characters, lowercase letters, numbers, or hyphens")

            # AWS specific validation
            elif cloud_provider == 'aws':
                if not kwargs.get('aws_access_key_id'):
                    errors.append("aws_access_key_id is required when cloud_provider is aws")
                if not kwargs.get('aws_secret_access_key'):
                    errors.append("aws_secret_access_key is required when cloud_provider is aws")
                if not kwargs.get('aws_region'):
                    errors.append("aws_region is required when cloud_provider is aws")

            # Azure specific validation
            elif cloud_provider == 'azure':
                if not kwargs.get('azure_client_id'):
                    errors.append("azure_client_id is required when cloud_provider is azure")
                if not kwargs.get('azure_client_secret'):
                    errors.append("azure_client_secret is required when cloud_provider is azure")

        # Data Warehouse Platform Validation
        if data_warehouse_platform:
            # BigQuery specific validation
            if data_warehouse_platform == 'bigquery':
                if not kwargs.get('bigquery_project_id'):
                    errors.append("bigquery_project_id is required when data_warehouse_platform is bigquery")
                if not kwargs.get('bigquery_region'):
                    errors.append("bigquery_region is required when data_warehouse_platform is bigquery")
                if not kwargs.get('data_platform_sa_json'):
                    errors.append("data_platform_sa_json (service account JSON) is required when using BigQuery")
                if not kwargs.get('data_analysis_sa_json'):
                    errors.append("data_analysis_sa_json (service account JSON) is required when using BigQuery")
                
                # Validate service account JSON format if provided
                for sa_field in ['data_platform_sa_json', 'data_analysis_sa_json']:
                    sa_json = kwargs.get(sa_field)
                    if sa_json:
                        try:
                            if cls._is_base64(sa_json):
                                decoded_json = base64.b64decode(sa_json).decode('utf-8')
                                json.loads(decoded_json)
                            else:
                                json.loads(sa_json)
                        except Exception as e:
                            errors.append(f"Invalid {sa_field} format: {str(e)}")

            # Redshift specific validation
            elif data_warehouse_platform == 'redshift':
                required_fields = {
                    'redshift_host': 'Redshift host',
                    'redshift_database': 'Redshift database',
                    'redshift_port': 'Redshift port',
                    'redshift_user': 'Redshift user',
                    'redshift_password': 'Redshift password'
                }
                for field, description in required_fields.items():
                    if not kwargs.get(field):
                        errors.append(f"{description} is required when using Redshift")

            # Snowflake specific validation
            elif data_warehouse_platform == 'snowflake':
                required_fields = {
                    'snowflake_account': 'Snowflake account',
                    'snowflake_user': 'Snowflake user',
                    'snowflake_warehouse': 'Snowflake warehouse',
                    'snowflake_database': 'Snowflake database'
                }
                for field, description in required_fields.items():
                    if not kwargs.get(field):
                        errors.append(f"{description} is required when using Snowflake")

                # Check if any authentication method is provided
                auth_methods = {
                    'password': kwargs.get('snowflake_password'),
                    'key_pair': all([kwargs.get('snowflake_private_key'), kwargs.get('snowflake_public_key')])
                }
                
                # If no authentication method is provided, generate keys and passphrase
                if not any(auth_methods.values()):
                    logger.info("No Snowflake authentication method provided. Generating key pair and passphrase.")
                    private_key, public_key = cls.generate_snowflake_keys()
                    kwargs['snowflake_private_key'] = private_key
                    kwargs['snowflake_public_key'] = public_key
                    kwargs['snowflake_passphrase'] = cls.generate_secure_password(length=32)
                # If password is provided but key pair is not, that's fine
                elif auth_methods['password'] and not auth_methods['key_pair']:
                    logger.info("Using password authentication for Snowflake.")
                # If key pair is provided but password is not, that's fine
                elif auth_methods['key_pair'] and not auth_methods['password']:
                    logger.info("Using key pair authentication for Snowflake.")
                    if not kwargs.get('snowflake_passphrase'):
                        kwargs['snowflake_passphrase'] = cls.generate_secure_password(length=32)
                # If both are provided, prefer key pair
                elif all(auth_methods.values()):
                    logger.info("Both password and key pair provided for Snowflake. Using key pair authentication.")
                    if not kwargs.get('snowflake_passphrase'):
                        kwargs['snowflake_passphrase'] = cls.generate_secure_password(length=32)

            # MS Fabric specific validation
            elif data_warehouse_platform == 'fabric':
                required_fields = {
                    'fabric_server': 'MS Fabric server',
                    'fabric_database': 'MS Fabric database',
                    'fabric_port': 'MS Fabric port',
                    'fabric_user': 'MS Fabric user',
                    'fabric_password': 'MS Fabric password',
                    'fabric_authentication': 'MS Fabric authentication method'
                }
                for field, description in required_fields.items():
                    if not kwargs.get(field):
                        errors.append(f"{description} is required when using MS Fabric")

        # Git provider validation
        git_provider = kwargs.get('git_provider')
        if git_provider:
            if git_provider not in ['github', 'gitlab', 'bitbucket']:
                errors.append("git_provider must be one of: github, gitlab, bitbucket")
            if not kwargs.get('git_provider_access_token') and kwargs.get('repo_access_method') != 'deploy_keys':
                errors.append("Either git_provider_access_token or deploy_keys repo_access_method is required")

        # URL format validation
        for url_field in ['dag_repo_url', 'data_repo_url']:
            url = kwargs.get(url_field)
            if url:
                if not url.startswith(('http://', 'https://')):
                    errors.append(f"{url_field} must start with http:// or https://")
                if git_provider == 'gitlab' and 'gitlab' not in url:
                    errors.append(f"{url_field} must be a GitLab URL when git_provider is gitlab")

        # SMTP validation - all or none
        smtp_fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password']
        smtp_provided = any(kwargs.get(field) for field in smtp_fields)
        if smtp_provided:
            for field in smtp_fields:
                if not kwargs.get(field):
                    errors.append(f"{field} is required when any SMTP setting is provided")
            try:
                smtp_port = int(kwargs.get('smtp_port', ''))
                if not (0 < smtp_port < 65536):
                    errors.append("smtp_port must be between 1 and 65535")
            except ValueError:
                errors.append("smtp_port must be a valid number")

        # Validate Looker configuration
        if kwargs.get('data_analysis_platform') == 'looker':
            if not all([kwargs.get('lookersdk_base_url'), kwargs.get('lookersdk_client_id'), kwargs.get('lookersdk_client_secret')]):
                errors.append("Looker SDK configuration (base_url, client_id, client_secret) is required when data_analysis_platform is looker")

        if errors:
            error_message = "Validation errors found:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_message)

    @classmethod
    def from_api_request(cls, json_data):
        """Factory method to create instance from API request data with validation"""
        params = {
            'client_id': json_data.get('client_id'),
            'client_secret': json_data.get('client_secret'),
            'customer': json_data.get('customer'),
            'user_email': json_data.get('user_email'),
            'method': json_data.get('method'),
            'data_analysis_platform': json_data.get('data_analysis_platform'),
            'data_warehouse_platform': json_data.get('data_warehouse_platform'),
            'git_provider': json_data.get('git_provider'),
            'dag_repo_url': json_data.get('dag_repo_url'),
            'data_repo_url': json_data.get('data_repo_url'),
            'data_repo_main_branch': json_data.get('data_repo_main_branch'),
            'repo_access_method': json_data.get('repo_access_method'),
            'project_id': json_data.get('project_id'),
            'project_region': json_data.get('project_region'),
            'cloud_provider': json_data.get('cloud_provider'),
            'git_provider_access_token': json_data.get('git_provider_access_token'),
            'private_key_orchestrator': json_data.get('private_key_orchestrator'),
            'public_key_orchestrator': json_data.get('public_key_orchestrator'),
            'private_key_data_model': json_data.get('private_key_data_model'),
            'public_key_data_model': json_data.get('public_key_data_model'),
            'smtp_host': json_data.get('smtp_host'),
            'smtp_port': json_data.get('smtp_port'),
            'smtp_username': json_data.get('smtp_username'),
            'smtp_password': json_data.get('smtp_password'),
            'orchestrator_platform': json_data.get('orchestrator_platform'),
            'lookersdk_base_url': json_data.get('lookersdk_base_url'),
            'lookersdk_client_id': json_data.get('lookersdk_client_id'),
            'lookersdk_client_secret': json_data.get('lookersdk_client_secret'),
            'data_platform_sa_json': json_data.get('data_platform_sa_json'),
            'data_analysis_sa_json': json_data.get('data_analysis_sa_json'),
            'bigquery_project_id': json_data.get('bigquery_project_id'),
            'bigquery_region': json_data.get('bigquery_region'),
            'aws_access_key_id': json_data.get('aws_access_key_id'),
            'aws_secret_access_key': json_data.get('aws_secret_access_key'),
            'aws_region': json_data.get('aws_region'),
            'azure_client_id': json_data.get('azure_client_id'),
            'azure_client_secret': json_data.get('azure_client_secret'),
            'runner_registration_token': json_data.get('runner_registration_token')
        }
        # Validate parameters before creating instance
        cls.validate_inputs(**params)
        return cls(**params)

    @classmethod
    def from_cli_args(cls, args):
        """Factory method to create instance from CLI arguments with validation"""
        params = {
            'client_id': args.client_id,
            'client_secret': args.client_secret,
            'customer': args.customer,
            'user_email': args.user_email,
            'method': args.method,
            'domain_name': args.domain_name,
            'data_analysis_platform': args.data_analysis_platform,
            'data_warehouse_platform': args.data_warehouse_platform,
            'git_provider': args.git_provider,
            'dag_repo_url': args.dag_repo_url,
            'data_repo_url': args.data_repo_url,
            'data_repo_main_branch': args.data_repo_main_branch,
            'repo_access_method': args.repo_access_method,
            'project_id': args.project_id,
            'project_region': args.project_region,
            'cloud_provider': args.cloud_provider,
            'git_provider_access_token': args.git_provider_access_token,
            'private_key_orchestrator': args.private_key_orchestrator,
            'public_key_orchestrator': args.public_key_orchestrator,
            'private_key_data_model': args.private_key_data_model,
            'public_key_data_model': args.public_key_data_model,
            'smtp_host': args.smtp_host,
            'smtp_port': args.smtp_port,
            'smtp_username': args.smtp_username,
            'smtp_password': args.smtp_password,
            'orchestrator_platform': args.orchestrator_platform,
            'lookersdk_base_url': args.lookersdk_base_url,
            'lookersdk_client_id': args.lookersdk_client_id,
            'lookersdk_client_secret': args.lookersdk_client_secret,
            # Bigquery parameters
            'data_platform_sa_json': args.data_platform_sa_json,
            'data_analysis_sa_json': args.data_analysis_sa_json,
            'bigquery_project_id': args.bigquery_project_id,
            'bigquery_region': args.bigquery_region,
            # Redshift parameters
            'redshift_host': args.redshift_host,
            'redshift_database': args.redshift_database,
            'redshift_port': args.redshift_port,
            'redshift_user': args.redshift_user,
            'redshift_password': args.redshift_password,
            # Snowflake parameters
            'snowflake_account': args.snowflake_account,
            'snowflake_user': args.snowflake_user,
            'snowflake_warehouse': args.snowflake_warehouse,
            'snowflake_database': args.snowflake_database,
            'snowflake_password': args.snowflake_password,
            'snowflake_private_key': args.snowflake_private_key,
            'snowflake_public_key': args.snowflake_public_key,
            'snowflake_passphrase': args.snowflake_passphrase,
            # MS Fabric parameters
            'fabric_server': args.fabric_server,
            'fabric_database': args.fabric_database,
            'fabric_port': args.fabric_port,
            'fabric_user': args.fabric_user,
            'fabric_password': args.fabric_password,
            'fabric_authentication': args.fabric_authentication,
            #Platform Auth
            'aws_access_key_id': args.aws_access_key_id,
            'aws_secret_access_key': args.aws_secret_access_key,
            'aws_region': args.aws_region,
            'azure_client_id': args.azure_client_id,
            'azure_client_secret': args.azure_client_secret,
            'runner_registration_token': args.runner_registration_token
        }
        # Validate parameters before creating instance
        cls.validate_inputs(**params)
        return cls(**params)


# Main execution of the script if this file is run as a script 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Customer Secret Manager - Tool for managing customer vault secrets",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Method group (mutually exclusive)
    method_group = parser.add_argument_group('vault method')
    method_group.add_argument(
        '--method',
        choices=['external_infisical', 'local_vault'],
        required=True,
        help='Vault method to use. Choose between external Infisical service or local HashiCorp vault'
    )

    # Required core arguments
    required_args = parser.add_argument_group('required core arguments')
    required_args.add_argument(
        '--customer',
        required=True,
        help='Customer tenant name (lowercase letters, numbers, and hyphens only)'
    )
    required_args.add_argument(
        '--domain_name',
        required=True,
        help='Domain name for the customer'
    )
    required_args.add_argument(
        '--user_email',
        required=True,
        help='Fast.BI Support Admin email for workspace access'
    )
    required_args.add_argument(
        '--data_analysis_platform',
        required=True,
        choices=['lightdash', 'looker', 'metabase', 'superset'],
        help='Data analysis platform to be used'
    )
    required_args.add_argument(
        '--data_warehouse_platform',
        choices=['bigquery', 'snowflake', 'redshift', 'fabric'],
        required=True,
        help='Data warehouse platform to use'
    )

    # Git configuration group
    git_group = parser.add_argument_group('git configuration')
    git_group.add_argument(
        '--git_provider',
        required=True,
        choices=['fastbi', 'github', 'gitlab', 'bitbucket'],
        help='Git provider for repositories'
    )
    git_group.add_argument(
        '--dag_repo_url',
        required=True,
        help='URL of the DAG repository for orchestration code (must match git provider)'
    )
    git_group.add_argument(
        '--data_repo_url',
        required=True,
        help='URL of the data repository for data models (must match git provider)'
    )
    git_group.add_argument(
        '--data_repo_main_branch',
        default='master',
        help='Main branch of the data repository (default: master)'
    )
    git_group.add_argument(
        '--repo_access_method',
        choices=['access_token', 'deploy_keys'],
        default='access_token',
        help='Method for repository access (default: access_token)'
    )
    git_group.add_argument(
        '--git_provider_access_token',
        help='Access token for Git provider (required if repo_access_method is access_token)'
    )
    git_group.add_argument(
        '--runner_registration_token',
        help='GitLab runner registration token (optional)'
    )

    # Cloud provider configuration
    cloud_group = parser.add_argument_group('cloud provider configuration')
    cloud_group.add_argument(
        '--cloud_provider',
        choices=['gcp', 'aws', 'azure', 'self-managed'],
        help='Cloud provider for infrastructure'
    )
    cloud_group.add_argument(
        '--project_id',
        help='Cloud project identifier (required if cloud_provider is specified)'
    )
    cloud_group.add_argument(
        '--project_region',
        help='Cloud project region (required if cloud_provider is specified)'
    )

    # External Infisical specific arguments
    infisical_group = parser.add_argument_group('external infisical configuration')
    infisical_group.add_argument(
        '--client_id',
        help='Infisical Client ID (required if method is external_infisical)'
    )
    infisical_group.add_argument(
        '--client_secret',
        help='Infisical Client Secret (required if method is external_infisical)'
    )

    # SSH Keys configuration
    ssh_group = parser.add_argument_group('ssh keys configuration')
    ssh_group.add_argument(
        '--private_key_orchestrator',
        help='Private key for orchestrator (required if repo_access_method is deploy_keys)'
    )
    ssh_group.add_argument(
        '--public_key_orchestrator',
        help='Public key for orchestrator (required if repo_access_method is deploy_keys)'
    )
    ssh_group.add_argument(
        '--private_key_data_model',
        help='Private key for data model (required if repo_access_method is deploy_keys)'
    )
    ssh_group.add_argument(
        '--public_key_data_model',
        help='Public key for data model (required if repo_access_method is deploy_keys)'
    )

    # SMTP configuration
    smtp_group = parser.add_argument_group('smtp configuration (all required if any is provided)')
    smtp_group.add_argument(
        '--smtp_host',
        help='SMTP server hostname'
    )
    smtp_group.add_argument(
        '--smtp_port',
        type=int,
        help='SMTP server port (1-65535)'
    )
    smtp_group.add_argument(
        '--smtp_username',
        help='SMTP authentication username'
    )
    smtp_group.add_argument(
        '--smtp_password',
        help='SMTP authentication password'
    )

    # Additional configuration
    additional_group = parser.add_argument_group('additional configuration')
    additional_group.add_argument(
        '--orchestrator_platform',
        default='Airflow',
        help='Orchestration platform (default: Airflow)'
    )
    additional_group.add_argument(
        '--lookersdk_base_url',
        help='Looker SDK base URL (required if data_analysis_platform is looker)'
    )
    additional_group.add_argument(
        '--lookersdk_client_id',
        help='Looker SDK client ID (required if data_analysis_platform is looker)'
    )
    additional_group.add_argument(
        '--lookersdk_client_secret',
        help='Looker SDK client secret (required if data_analysis_platform is looker)'
    )

    # BigQuery configuration
    bigquery_group = parser.add_argument_group('bigquery configuration')
    bigquery_group.add_argument(
        '--bigquery_project_id',
        help='BigQuery project ID (required if data_warehouse_platform is bigquery)'
    )
    bigquery_group.add_argument(
        '--bigquery_region',
        help='BigQuery region (required if data_warehouse_platform is bigquery)'
    )
    bigquery_group.add_argument(
        '--data_platform_sa_json',
        help='Base64 encoded or raw JSON service account key for data platform (required if data_warehouse_platform is bigquery)'
    )
    bigquery_group.add_argument(
        '--data_analysis_sa_json',
        help='Base64 encoded or raw JSON service account key for data analysis (required if data_warehouse_platform is bigquery)'
    )

    # Redshift configuration
    redshift_group = parser.add_argument_group('redshift configuration')
    redshift_group.add_argument(
        '--redshift_host',
        help='Redshift cluster hostname (required if data_warehouse_platform is redshift)'
    )
    redshift_group.add_argument(
        '--redshift_database',
        help='Redshift database name (required if data_warehouse_platform is redshift)'
    )
    redshift_group.add_argument(
        '--redshift_port',
        help='Redshift port (default: 5439)'
    )
    redshift_group.add_argument(
        '--redshift_user',
        help='Redshift username (required if data_warehouse_platform is redshift)'
    )
    redshift_group.add_argument(
        '--redshift_password',
        help='Redshift password (required if data_warehouse_platform is redshift)'
    )

    # Snowflake configuration
    snowflake_group = parser.add_argument_group('snowflake configuration')
    snowflake_group.add_argument(
        '--snowflake_account',
        help='Snowflake account identifier (required if data_warehouse_platform is snowflake)'
    )
    snowflake_group.add_argument(
        '--snowflake_user',
        help='Snowflake username (required if data_warehouse_platform is snowflake)'
    )
    snowflake_group.add_argument(
        '--snowflake_warehouse',
        help='Snowflake warehouse name (required if data_warehouse_platform is snowflake)'
    )
    snowflake_group.add_argument(
        '--snowflake_database',
        help='Snowflake database name (required if data_warehouse_platform is snowflake)'
    )
    snowflake_group.add_argument(
        '--snowflake_password',
        help='Snowflake password (optional if using key pair authentication)'
    )
    snowflake_group.add_argument(
        '--snowflake_private_key',
        help='Snowflake private key (optional if using password authentication)'
    )
    snowflake_group.add_argument(
        '--snowflake_public_key',
        help='Snowflake public key (optional if using password authentication)'
    )
    snowflake_group.add_argument(
        '--snowflake_passphrase',
        help='Snowflake passphrase for private key (optional if using password authentication)'
    )

    # MS Fabric configuration
    fabric_group = parser.add_argument_group('ms fabric configuration')
    fabric_group.add_argument(
        '--fabric_server',
        help='MS Fabric server hostname (required if data_warehouse_platform is fabric)'
    )
    fabric_group.add_argument(
        '--fabric_database',
        help='MS Fabric database name (required if data_warehouse_platform is fabric)'
    )
    fabric_group.add_argument(
        '--fabric_port',
        help='MS Fabric port (default: 1433)'
    )
    fabric_group.add_argument(
        '--fabric_user',
        help='MS Fabric username (required if data_warehouse_platform is fabric)'
    )
    fabric_group.add_argument(
        '--fabric_password',
        help='MS Fabric password (required if data_warehouse_platform is fabric)'
    )
    fabric_group.add_argument(
        '--fabric_authentication',
        help='MS Fabric authentication method (required if data_warehouse_platform is fabric)'
    )

    # AWS configuration
    aws_group = parser.add_argument_group('aws configuration')
    aws_group.add_argument(
        '--aws_access_key_id',
        help='AWS access key ID (required if cloud_provider is aws)'
    )
    aws_group.add_argument(
        '--aws_secret_access_key',
        help='AWS secret access key (required if cloud_provider is aws)'
    )
    aws_group.add_argument(
        '--aws_region',
        help='AWS region (required if cloud_provider is aws)'
    )


    # Azure configuration
    azure_group = parser.add_argument_group('azure configuration')
    azure_group.add_argument(
        '--azure_client_id',
        help='Azure client ID (required if cloud_provider is azure)'
    )
    azure_group.add_argument(
        '--azure_client_secret',
        help='Azure client secret (required if cloud_provider is azure)'
    )

    # Parse arguments
    args = parser.parse_args()

    # Additional validation
    errors = []

    # Validate method-specific requirements
    if args.method == 'external_infisical':
        if not args.client_id:
            errors.append("--client_id is required for external_infisical method")
        if not args.client_secret:
            errors.append("--client_secret is required for external_infisical method")

    # Validate git provider access
    if args.repo_access_method == 'access_token' and not args.git_provider_access_token:
        errors.append("--git_provider_access_token is required when repo_access_method is access_token")
    elif args.repo_access_method == 'deploy_keys':
        if not all([args.private_key_orchestrator, args.public_key_orchestrator,
                   args.private_key_data_model, args.public_key_data_model]):
            errors.append("All SSH keys are required when repo_access_method is deploy_keys")

    # Validate cloud provider requirements
    if args.cloud_provider:
        if args.cloud_provider not in ['gcp', 'aws', 'azure', 'self-managed']:
            errors.append("cloud_provider must be one of: gcp, aws, azure, self-managed")

        # GCP specific validation
        if args.cloud_provider == 'gcp':
            if not args.project_id:
                errors.append("project_id is required when cloud_provider is gcp")
            if not args.project_region:
                errors.append("project_region is required when cloud_provider is gcp")
            
            project_id = args.project_id
            if project_id and not re.match(r'^[a-z][-a-z0-9]{4,28}[a-z0-9]$', project_id):
                errors.append("GCP project_id must be 6-30 characters, lowercase letters, numbers, or hyphens")
        
        # AWS specific validation
        elif args.cloud_provider == 'aws':
            if not args.aws_access_key_id:
                errors.append("aws_access_key_id is required when cloud_provider is aws")
            if not args.aws_secret_access_key:
                errors.append("aws_secret_access_key is required when cloud_provider is aws")
            if not args.aws_region:
                errors.append("aws_region is required when cloud_provider is aws")

        # Azure specific validation
        elif args.cloud_provider == 'azure':
            if not args.azure_client_id:
                errors.append("azure_client_id is required when cloud_provider is azure")
            if not args.azure_client_secret:
                errors.append("azure_client_secret is required when cloud_provider is azure")

    # Validate SMTP configuration
    smtp_fields = [args.smtp_host, args.smtp_port, args.smtp_username, args.smtp_password]
    if any(smtp_fields) and not all(smtp_fields):
        errors.append("All SMTP fields (host, port, username, password) are required when any SMTP field is provided")

    # Validate Looker configuration
    if args.data_analysis_platform == 'looker':
        if not all([args.lookersdk_base_url, args.lookersdk_client_id, args.lookersdk_client_secret]):
            errors.append("Looker SDK configuration (base_url, client_id, client_secret) is required when data_analysis_platform is looker")

    # Validate BigQuery configuration
    if args.data_warehouse_platform == 'bigquery':
        if not args.data_platform_sa_json:
            errors.append("--data_platform_sa_json is required when data_warehouse_platform is bigquery")
        if not args.data_analysis_sa_json:
            errors.append("--data_analysis_sa_json is required when data_warehouse_platform is bigquery")

    if errors:
        parser.error("\n".join(errors))

    try:
        # Create manager instance using the CLI factory method
        manager = CustomerSecretManager.from_cli_args(args)
        results = manager.run()
        print("Execution Results:")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print("An error occurred during execution:")
        print(str(e))
        sys.exit(1)