import subprocess
import os
import base64
from datetime import datetime
import json
from jinja2 import Environment, FileSystemLoader
import argparse
import sys

class SecretManager:
    def __init__(self, chart_version, customer, metadata_collector, external_infisical_host=None, slug=None, secret_manager_client_id=None, secret_manager_client_secret=None, cluster_name=None, kube_config_path=None, hc_vault_chart_version=None,  namespace="vault", method="local_vault"):
        self.deployment_environment = "infrastructure-services"
        self.namespace = namespace
        self.project_slug = slug
        self.infisical_environment = "prod"
        self.secret_manager_client_id = secret_manager_client_id
        self.secret_manager_client_secret = secret_manager_client_secret
        self.external_infisical_host = external_infisical_host
        self.customer = customer
        self.metadata_collector = metadata_collector
        self.cluster_name = cluster_name if cluster_name else f"fast-bi-{customer}-platform"
        self.kube_config = kube_config_path if kube_config_path else f'/tmp/{self.cluster_name}-kubeconfig.yaml'
        #Service specific 
        self.method=method
        if method=="local_vault":
            self.chart_version_hc_vault = hc_vault_chart_version
            self.deployment_name_vault = "vault"
            self.chart_repo_name_hc_vault = "hashicorp"
            self.chart_repo_hc_vault = "https://helm.releases.hashicorp.com"
            self.chart_name_hc_vault = "hashicorp/vault"
            self.values_path_hc_vault = "charts/infra_services_charts/secret_manager/values.yaml"
            self.render_template_values_path_hc_vault = "charts/infra_services_charts/secret_manager/template_values.yaml"
            self.values_path_extra_hc_vault = "charts/infra_services_charts/secret_manager/values_extra.yaml"
            self.render_template_values_extra_path_hc_vault = "charts/infra_services_charts/secret_manager/template_values_extra.yaml"
            self.secret_file = f"/tmp/{customer}_customer_vault_structure.json"
            self.chart_version = chart_version
            self.deployment_name = "secret-operator"
            self.chart_repo_name = "external-secrets"
            self.chart_repo = "https://charts.external-secrets.io"
            self.chart_name = "external-secrets/external-secrets"
            self.values_path = "charts/infra_services_charts/secret_manager_operator/values.yaml"
            self.values_extra_path = "charts/infra_services_charts/secret_manager_operator/values_extra.yaml"
            self.render_template_values_path = "charts/infra_services_charts/secret_manager_operator/template_values.yaml"
            self.render_template_values_extra_path = "charts/infra_services_charts/secret_manager_operator/template_values_extra.yaml"
        if method=="external_infisical":
            self.chart_version = chart_version
            self.deployment_name = "secret-operator"
            self.chart_repo_name = "infisical"
            self.chart_repo = "https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/"
            self.chart_name = "infisical/secrets-operator"
            self.values_path = "charts/infra_services_charts/secret_manager_operator/values.yaml"
            self.values_extra_path = "charts/infra_services_charts/secret_manager_operator/values_extra.yaml"
            self.render_template_values_path = "charts/infra_services_charts/secret_manager_operator/template_values.yaml"
            self.render_template_values_extra_path = "charts/infra_services_charts/secret_manager_operator/template_values_extra.yaml"
        #MetadataCollection
        self.app_name = self.chart_name.split('/')[1]

    def deploy_service(self, chart_repo_name, chart_repo, deployment_name, chart_name, chart_version, namespace, values_path ):
        # Properly add and update the Helm repo
        self.execute_command(["helm", "repo", "add", chart_repo_name, chart_repo])
        self.execute_command(["helm", "repo", "update", chart_repo_name])
        # Formulate the Helm upgrade command properly as a list
        helm_command = [
            "helm", "upgrade", "-i", deployment_name, chart_name,
            "--version", chart_version,
            "--namespace", namespace,
            "--create-namespace",
            "--wait",
            "--values", values_path,
            "--kubeconfig", self.kube_config
        ]
        self.execute_command(helm_command)

    def get_deployed_app_version(self, deployment_name, namespace ):
        command = ["helm", "ls", "--deployed", "-f", deployment_name, "-n", namespace, "--kubeconfig", self.kube_config, "--output", "json"]
        result = self.execute_command(command)
        if result:
            # Parse JSON output
            deployments = json.loads(result)
            if deployments and isinstance(deployments, list):
                # Assuming there's only one matching deployment
                return deployments[0]['app_version']
        return "No deployed version found"

    def deploy_extra_service(self, extra_value_path, namespace):
        kubectl_command = [
            "kubectl", "apply", "-f", extra_value_path, "--namespace", namespace, "--kubeconfig", self.kube_config
        ]
        self.execute_command(kubectl_command)

    def deploy_extra_secrets(self, secret_value_path, namespace):
        """Deploy secrets using kubectl apply, which is idempotent and can be run multiple times"""
        # First, create a temporary file with the secret manifest
        secret_manifest = f"""
apiVersion: v1
kind: Secret
metadata:
  name: vault-secrets
  namespace: {namespace}
type: Opaque
data:
  vault-secrets.json: {self._get_base64_encoded_file_content(secret_value_path)}
"""
        # Write the manifest to a temporary file
        temp_manifest_path = f"/tmp/vault-secrets-{namespace}.yaml"
        with open(temp_manifest_path, 'w') as f:
            f.write(secret_manifest)
        
        # Apply the secret manifest
        kubectl_apply_command = [
            "kubectl", "apply", "-f", temp_manifest_path, "--kubeconfig", self.kube_config
        ]
        self.execute_command(kubectl_apply_command)
        
        # Clean up the temporary file
        if os.path.exists(temp_manifest_path):
            os.remove(temp_manifest_path)
    
    def _get_base64_encoded_file_content(self, file_path):
        """Get base64 encoded content of a file"""
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def execute_command(self, command):
        try:
            print("Executing command:", ' '.join(command))
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print("Command output:", result.stdout)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e.cmd}")
            print(f"Status code: {e.returncode}")
            print(f"Output: {e.stdout}")
            print(f"Error: {e.stderr}")
            raise Exception(f"Execution failed for command {' '.join(command)}: {e.stderr}")

    def render_values_file(self, chart_name, chart_repo, chart_version ):
        context = {
            'chart_name': chart_name,
            'chart_repo': chart_repo,
            'chart_version': chart_version
        }
        self.render_template(self.render_template_values_path, self.values_path, context)

    def render_template(self, template_path, output_path, context):
        env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
        template = env.get_template(os.path.basename(template_path))
        output = template.render(context)
        with open(output_path, 'w') as f:
            f.write(output)

    def run(self):
        # Validate and deploy based on method
        if self.method == "local_vault":
            # Check if secret file exists
            if not os.path.exists(self.secret_file):
                raise FileNotFoundError(f"Secret file not found: {self.secret_file}")
            
            # Render HashiCorp Vault values files
            vault_context = {
                'chart_name': self.chart_name_hc_vault,
                'chart_repo': self.chart_repo_hc_vault,
                'chart_version': self.chart_version_hc_vault
            }
            self.render_template(self.render_template_values_path_hc_vault, self.values_path_hc_vault, vault_context)
            self.render_template(self.render_template_values_extra_path_hc_vault, self.values_path_extra_hc_vault, vault_context)

            # Deploy HashiCorp Vault
            self.deploy_service(
                self.chart_repo_name_hc_vault,
                self.chart_repo_hc_vault,
                self.deployment_name_vault,
                self.chart_name_hc_vault,
                self.chart_version_hc_vault,
                self.namespace,
                self.values_path_hc_vault
            )
            # Deploy vault secrets
            self.deploy_extra_secrets(self.secret_file, self.namespace)
            
            # Deploy extra Kubernetes resources for Vault
            self.deploy_extra_service(self.values_path_extra_hc_vault, self.namespace)
        
        
        # Render and deploy External Secrets Operator
        operator_context = {
            'chart_name': self.chart_name,
            'chart_repo': self.chart_repo,
            'chart_version': self.chart_version,
            'namespace': self.namespace,
            'method': self.method,
            'secret_manager_client_id': self.secret_manager_client_id,
            'secret_manager_client_secret': self.secret_manager_client_secret,
            'external_infisical_host': self.external_infisical_host,
            'project_slug': self.project_slug,
            'infisical_environment': self.infisical_environment
        }
        self.render_template(self.render_template_values_path, self.values_path, operator_context)
        self.render_template(self.render_template_values_extra_path, self.values_extra_path, operator_context)
        
        # Deploy External Secrets Operator
        self.deploy_service(
            self.chart_repo_name,
            self.chart_repo,
            self.deployment_name,
            self.chart_name,
            self.chart_version,
            self.namespace,
            self.values_path
        )

        self.deploy_extra_service(self.values_extra_path, self.namespace)
        
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
            "deploy_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        self.metadata_collector.add_deployment_record(deployment_record)
        return "Secret Manager and Operator deployed successfully"

    @classmethod
    def from_cli_args(cls, args):
        """Create a SecretManager instance from CLI arguments"""
        return cls(
            external_infisical_host=args.external_infisical_host,
            slug=args.project_slug,
            secret_manager_client_id=args.client_id,
            secret_manager_client_secret=args.client_secret,
            chart_version=args.chart_version,
            customer=args.customer,
            metadata_collector=args.metadata_collector,
            cluster_name=args.cluster_name,
            kube_config_path=args.kube_config_path,
            hc_vault_chart_version=args.hc_vault_chart_version,
            namespace=args.namespace,
            method=args.method
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Secret Manager Deployment Tool",
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
        help='Chart version for the external-secrets operator'
    )

    # Optional arguments
    optional_args = parser.add_argument_group('optional arguments')
    optional_args.add_argument(
        '--external_infisical_host',
        help='External Infisical host (required if method is external_infisical)'
    )
    optional_args.add_argument(
        '--client_id',
        help='Secret manager client ID (required if method is external_infisical)'
    )
    optional_args.add_argument(
        '--client_secret',
        help='Secret manager client secret (required if method is external_infisical)'
    )
    optional_args.add_argument(
        '--project_slug',
        help='Project slug for the vault'
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
        '--hc_vault_chart_version',
        help='HashiCorp Vault chart version (required if method is local_vault)'
    )
    optional_args.add_argument(
        '--namespace',
        default='vault',
        help='Kubernetes namespace for deployment (default: vault)'
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
    elif args.method == 'local_vault':
        if not args.hc_vault_chart_version:
            errors.append("--hc_vault_chart_version is required for local_vault method")

    if errors:
        parser.error("\n".join(errors))

    try:
        # Create a simple metadata collector for CLI usage
        class SimpleMetadataCollector:
            def __init__(self, metadata_file):
                self.metadata_file = metadata_file
                self.deployment_records = []
                # Load existing records if file exists
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r') as f:
                            self.deployment_records = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse {metadata_file}, starting with empty records")
                        self.deployment_records = []
            
            def add_deployment_record(self, record):
                self.deployment_records.append(record)
                # Write to file
                with open(self.metadata_file, 'w') as f:
                    json.dump(self.deployment_records, f, indent=2)
                print(f"Deployment record added to {self.metadata_file}")
        
        # Use the appropriate metadata collector
        if args.skip_metadata:
            # Create a dummy metadata collector that does nothing
            class DummyMetadataCollector:
                def add_deployment_record(self, record):
                    print("Metadata collection skipped")
            
            metadata_collector = DummyMetadataCollector()
        else:
            # Use the simple file-based collector
            metadata_collector = SimpleMetadataCollector(args.metadata_file)
        
        # Add metadata collector to args for from_cli_args method
        args.metadata_collector = metadata_collector
        
        # Create manager instance using the CLI factory method
        manager = SecretManager.from_cli_args(args)
        result = manager.run()
        print("Execution Result:")
        print(result)
    except Exception as e:
        print("An error occurred during execution:")
        print(str(e))
        sys.exit(1)