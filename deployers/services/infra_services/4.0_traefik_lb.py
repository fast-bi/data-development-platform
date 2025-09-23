import subprocess
import os
import datetime
from datetime import datetime
import json
import sys
import argparse
import logging
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
logger = logging.getLogger('traefik_ingress_deployer')

class TraefikIngress:
    def __init__(self, chart_version, customer, whitelisted_environment_ips, metadata_collector, 
                 cloud_provider, domain_name, project_id=None, cluster_name=None, region=None, 
                 kube_config_path=None, external_ip=None, namespace="traefik-ingress"):
        self.deployment_environment = "infrastructure"        
        self.namespace = namespace
        self.customer = customer
        self.domain_name = domain_name
        self.cloud_provider = cloud_provider
        self.whitelisted_environment_ips = [whitelisted_environment_ips] if isinstance(whitelisted_environment_ips, str) else whitelisted_environment_ips
        self.metadata_collector = metadata_collector
        
        # Cloud Provider Specific
        try:
            if self.cloud_provider == "gcp":
                self.project_id = project_id if project_id else f"fast-bi-{customer}"
                self.region = region if region else "europe-central2"
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

        # Set kubeconfig path after cluster_name is properly initialized
        self.kube_config = kube_config_path if kube_config_path else f'/tmp/{self.cluster_name}-kubeconfig.yaml'
        logger.info(f"Using kubeconfig: {self.kube_config}")
        
        # Check if kubeconfig exists
        if not os.path.exists(self.kube_config):
            logger.warning(f"Kubeconfig file not found at {self.kube_config}. Deployment may fail.")

        # Service specific
        self.chart_version = chart_version
        self.external_ip = external_ip
        self.customer_main_domain = f"{self.customer}.{self.domain_name}"
        self.deployment_name = "traefik-ingress"
        self.chart_repo_name = "traefik"
        self.chart_name = "traefik/traefik"
        self.chart_repo = "https://helm.traefik.io/traefik"
        self.values_path = f"charts/infra_services_charts/traefik_lb/values.yaml"
        self.render_template_values_path = f"charts/infra_services_charts/traefik_lb/template_values.yaml"
        
        # MetadataCollection
        self.app_name = self.chart_name.split('/')[1]
        
        # Validate template paths
        self._validate_template_paths()

    def _validate_template_paths(self):
        """Validate that all required template files exist"""
        template_path = Path(self.render_template_values_path)
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
                "--wait",
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

    def render_values_file(self):
        """Render the values file from template"""
        logger.info("Rendering values file from template")
        try:
            context = {
                'chart_name': self.chart_name,
                'chart_repo': self.chart_repo,
                'chart_version': self.chart_version,
                'project_id': self.project_id,
                'loadBalancerSourceRanges': self.whitelisted_environment_ips,
                'loadBalancerIP': self.external_ip,
                'customer': self.customer,
                "cloud_provider": self.cloud_provider,
                'customer_main_domain': self.customer_main_domain
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

    def render_template(self, template_path, output_path, context):
        """Render a Jinja2 template to a file"""
        try:
            logger.debug(f"Rendering template {template_path} to {output_path}")
            env = Environment(loader=FileSystemLoader(os.path.dirname(template_path)))
            template = env.get_template(os.path.basename(template_path))
            output = template.render(context)
            
            with open(output_path, 'w') as f:
                f.write(output)
            logger.debug(f"Template rendered successfully")
        except TemplateNotFound:
            logger.error(f"Template not found: {template_path}")
            raise FileNotFoundError(f"Template not found: {template_path}")
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {str(e)}")
            raise

    def run(self):
        """Main execution method"""
        logger.info(f"Starting Traefik Ingress deployment for customer: {self.customer}")
        try:
            # Deployment
            self.render_values_file()
            
            # Deploy the main service
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
                "customer_main_domain": self.customer_main_domain,
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
            logger.info("Traefik Ingress deployment completed successfully")
            return "Traefik Ingress deployed successfully"
        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            raise

    @classmethod
    def from_cli_args(cls, args):
        """Create a TraefikIngress instance from CLI arguments"""
        logger.info("Creating TraefikIngress instance from CLI arguments")
        return cls(
            chart_version=args.chart_version,
            customer=args.customer,
            whitelisted_environment_ips=args.whitelisted_environment_ips,
            metadata_collector=args.metadata_collector,
            cloud_provider=args.cloud_provider,
            project_id=args.project_id,
            cluster_name=args.cluster_name,
            domain_name=args.domain_name,
            region=args.region,
            kube_config_path=args.kube_config_path,
            external_ip=args.external_ip,
            namespace=args.namespace
        )

if __name__ == "__main__":
    # Configure file logging if running as main script
    log_file = "traefik_ingress_deployment.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Starting Traefik Ingress deployment script, logging to {log_file}")
    
    parser = argparse.ArgumentParser(
        description="Traefik Ingress Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    required_args = parser.add_argument_group('required arguments')
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
        '--chart_version',
        required=True,
        help='Chart version for traefik'
    )
    required_args.add_argument(
        '--whitelisted_environment_ips',
        required=True,
        nargs='+',
        help='Whitelisted IPs for the load balancer (space-separated list)'
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
        '--project_id',
        help='Cloud provider project ID (default: fast-bi-{customer} for GCP)'
    )
    optional_args.add_argument(
        '--cluster_name',
        help='Kubernetes cluster name (default: fast-bi-{customer}-platform)'
    )
    optional_args.add_argument(
        '--region',
        help='Cloud provider region (default: europe-central2 for GCP)'
    )
    optional_args.add_argument(
        '--kube_config_path',
        help='Path to kubeconfig file (default: /tmp/{cluster_name}-kubeconfig.yaml)'
    )
    optional_args.add_argument(
        '--external_ip',
        help='External IP address for the load balancer'
    )
    optional_args.add_argument(
        '--namespace',
        default='traefik-ingress',
        help='Kubernetes namespace for deployment (default: traefik-ingress)'
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
        logger.info(f"Deploying Traefik Ingress for customer: {args.customer}")
        logger.info(f"Cloud provider: {args.cloud_provider}")
        logger.info(f"Whitelisted IPs: {args.whitelisted_environment_ips}")
        
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
        logger.info("Creating TraefikIngress manager instance")
        manager = TraefikIngress.from_cli_args(args)
        
        # Run the deployment
        logger.info("Starting deployment process")
        result = manager.run()
        
        logger.info("Execution Result: " + result)
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
        logger.info("Traefik Ingress deployment script completed")