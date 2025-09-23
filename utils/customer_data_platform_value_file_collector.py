import requests
import os
import shutil
import subprocess
from cryptography.fernet import Fernet

class GitManager:
    """Manages Git operations such as creating projects and pushing files."""
    def __init__(self, access_token, base_url=None):
        self.base_url = base_url or os.getenv("GITLAB_API_LINK", "https://gitlab.fast.bi")
        self.access_token = access_token
        self.headers = {"Private-Token": self.access_token}

    def create_group(self, name, path, parent_id=None):
        """Create a GitLab group (or subgroup)."""
        url = f"{self.base_url}/api/v4/groups"
        data = {"name": name, "path": path.lower()}
        if parent_id:
            data["parent_id"] = parent_id
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to create group {name}: {response.status_code} {response.text}")
            return None
        return response.json()

    def create_project(self, name, namespace_id):
        """Create a GitLab project in the given namespace."""
        url = f"{self.base_url}/api/v4/projects"
        data = {"name": name, "namespace_id": namespace_id}
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to create project {name}: {response.status_code} {response.text}")
            return None
        return response.json()

    def create_access_token(self, group_id, token_name, scopes, expires_at, access_level):
        """Create an access token for a specific GitLab group."""
        url = f"{self.base_url}/api/v4/groups/{group_id}/access_tokens"
        data = {
            "name": token_name,
            "scopes": scopes,
            "expires_at": expires_at,
            "access_level": access_level
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to create access token {token_name}: {response.status_code} {response.text}")
            return None
        return response.json()

    def create_user(self, email, customer, force_random_password=True, external=True):
        """Create a main user for the customer in GitLab."""
        url = f"{self.base_url}/api/v4/users"
        customer_name = customer.capitalize()
        data = {
            "email": email,
            "external": external,
            "force_random_password": force_random_password,
            "name": f"{customer_name} Admin",
            "organization": customer_name,
            "username": f"admin-{customer.lower()}"
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to create user for {customer_name}: {response.status_code} {response.text}")
            return None
        return response.json()
    
    def add_ssh_key_to_user(self, user_id, ssh_key, title):
        """Add an SSH key to a specified user in GitLab."""
        url = f"{self.base_url}/api/v4/users/{user_id}/keys"
        data = {
            "title": title,
            "key": ssh_key
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to add SSH key for user ID {user_id}: {response.status_code} {response.text}")
            return None
        return response.json()
    
    def create_group_runner_access_token(self, group_id, description, tag_list, maximum_timeout=3600):
        """Create a GitLab group runner."""
        url = f"{self.base_url}/api/v4/user/runners"  # Corrected endpoint
        data = {
            "runner_type": "group_type",
            "group_id": group_id,
            "description": description,  # Note that 'description' was misspelled in your cURL as 'desription'
            "tag_list": tag_list,  # Assuming tag_list is a single tag string based on your cURL example
            "maximum_timeout": maximum_timeout
        }
        headers = {
            "PRIVATE-TOKEN": self.access_token,  # Include the token correctly
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 201:
            print(f"Failed to create group runner for group ID {group_id}: {response.status_code} {response.text}")
            return None
        return response.json()

    def create_group_variable(self, group_id, key, value, protected=False, masked=False, variable_type="env_var"):
        """Create a CI/CD variable for a specific GitLab group."""
        url = f"{self.base_url}/api/v4/groups/{group_id}/variables"
        data = {
            "key": key,
            "value": value,
            "protected": protected,
            "masked": masked,
            "raw": "false",
            "environment_scope": "*",
            "description": "fast.bi data platform CI workflow variables",
            "variable_type": variable_type 
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to create variable {key} for group ID {group_id}: {response.status_code} {response.text}")
            return None
        return response.json()

    def setup_project_structure(self, customer, parent_id):
        """Setup a complete project structure for a customer, including subgroup and project."""
        # Capitalize the first letter of the customer name for display purposes
        customer_name = customer.capitalize()
        # Create customer subgroup under the specified parent group
        customer_group = self.create_group(customer_name, customer, parent_id)
        if not customer_group:
            return None

        # Create a specific subgroup for Kubernetes core infrastructure services
        core_infrastructure_subgroup_name = 'core_infrastructure_services'
        k8s_core_services_subgroup_name = 'k8s_core_infrastructure_services'
        k8s_data_services_subgroup_name = 'k8s_data_services'

        core_infrastructure_subgroup = self.create_group(core_infrastructure_subgroup_name, core_infrastructure_subgroup_name.lower(), customer_group['id'])
        k8s_core_services_subgroup = self.create_group(k8s_core_services_subgroup_name, k8s_core_services_subgroup_name.lower(), customer_group['id'])
        k8s_data_services_subgroup = self.create_group(k8s_data_services_subgroup_name, k8s_data_services_subgroup_name.lower(), customer_group['id'])

        if not core_infrastructure_subgroup:
            return None
        if not k8s_core_services_subgroup:
            return None        
        if not k8s_data_services_subgroup:
            return None   
        
        # Create a project inside the k8s_core_infrastructure_services subgroup
        core_infrastructure_subgroup_project_name = f"{customer.lower()}_core_infrastructure_services"
        k8s_core_services_subgroup_project_name = f"{customer.lower()}_k8s_core_infrastructure_services"
        k8s_data_services_subgroup_project_name = f"{customer.lower()}_k8s_data_services"
        core_infrastructure_subgroup_project = self.create_project(core_infrastructure_subgroup_project_name, core_infrastructure_subgroup['id'])
        k8s_core_services_subgroup_project = self.create_project(k8s_core_services_subgroup_project_name, k8s_core_services_subgroup['id'])
        k8s_data_services_subgroup_project = self.create_project(k8s_data_services_subgroup_project_name, k8s_data_services_subgroup['id'])
        if not core_infrastructure_subgroup_project:
            return None
        if not k8s_core_services_subgroup_project:
            return None
        if not k8s_data_services_subgroup_project:
            return None

        return customer_group['web_url'], core_infrastructure_subgroup_project['http_url_to_repo'], k8s_core_services_subgroup_project['http_url_to_repo'], k8s_data_services_subgroup_project['http_url_to_repo']

    def construct_repo_url_with_token(repo_url, access_token):
        # Parse the URL to find the insertion point for the access token
        from urllib.parse import urlparse, urlunparse
        
        parsed_url = urlparse(repo_url)
        # Construct the new netloc with the access token
        new_netloc = f"oauth2:{access_token}@{parsed_url.hostname}"
        
        # Build the new URL with the access token embedded
        new_parsed_url = parsed_url._replace(netloc=new_netloc)
        return urlunparse(new_parsed_url)
    
    def grant_access_to_user_in_group(self, user_id, group_id, access_level=50):
        """Grant access to a user in a GitLab group."""
        url = f"{self.base_url}/api/v4/groups/{group_id}/members"
        data = {
            "user_id": user_id,
            "access_level": access_level
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 201:
            print(f"Failed to grant access to user ID {user_id} in group ID {group_id}: {response.status_code} {response.text}")
            return None
        return response.json()

class FileManager:
    """Handles file operations, including organization, encryption, and preparation for Git commits."""
    def __init__(self, encryption_key=None):
        if encryption_key:
            try:
                # Decodes the encryption key if it's provided as a string
                self.key = encryption_key.encode('utf-8')  # Store the key for later use
                self.fernet = Fernet(self.key)
            except Exception as e:
                print(f"Invalid encryption key provided: {str(e)}. Generating a new one.")
                self.key = Fernet.generate_key()  # Store and generate a new key
                self.fernet = Fernet(self.key)
        else:
            # Generates a new key if none is provided
            self.key = Fernet.generate_key()
            self.fernet = Fernet(self.key)

    def create_directories(self, base_dir, directories):
        """Create a directory structure based on a list of paths."""
        for directory in directories:
            full_path = os.path.join(base_dir, directory)
            os.makedirs(full_path, exist_ok=True)

    def copy_files(self, source_root, dest_root, mapping):
        """Copy files from the source directory to the destination based on a mapping of subdirectories and files."""
        for subdirectory, files in mapping.items():
            source_dir = os.path.join(source_root, subdirectory)
            dest_dir = os.path.join(dest_root, subdirectory)
            os.makedirs(dest_dir, exist_ok=True)  # Ensure destination directory exists
            for file_name in files:
                source_file = os.path.join(source_dir, file_name)
                dest_file = os.path.join(dest_dir, file_name)
                if os.path.exists(source_file):
                    shutil.copy(source_file, dest_file)

    def encrypt_files(self, directory):
        """Encrypt all files in a directory."""
        for root, dirs, files in os.walk(directory):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                with open(file_path, 'rb') as file:
                    file_data = file.read()
                encrypted_data = self.fernet.encrypt(file_data)
                with open(file_path, 'wb') as file:
                    file.write(encrypted_data)

    def prepare_files(self, source_root, dest_root, mapping):
        """Prepare the files by copying them and then encrypting them."""
        self.create_directories(dest_root, mapping.keys())
        self.copy_files(source_root, dest_root, mapping)
        self.encrypt_files(dest_root)

    def get_encryption_key(self):
        """Return the encryption key for external use."""
        return self.key.decode('utf-8')  # Return the key as a string for usage outside
    
    def init_git_repository(self, local_repo_path, remote_repo_url):
        """Initializes a git repository in the given local path and sets the remote origin."""
        subprocess.run(['git', 'init'], cwd=local_repo_path, check=True)
        subprocess.run(['git', 'remote', 'add', 'origin', remote_repo_url], cwd=local_repo_path, check=True)

    def commit_and_push(self, local_repo_path, commit_message="Updated encrypted configuration"):
        """Commits and pushes files from the local repository path to the remote repository."""
        subprocess.run(['git', 'add', '.'], cwd=local_repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', commit_message], cwd=local_repo_path, check=True)
        subprocess.run(['git', 'push', '-u', 'origin', 'master'], cwd=local_repo_path, check=True)
