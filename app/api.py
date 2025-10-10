import os
from flask import request, jsonify, send_file, current_app, render_template_string
import json
from flask import send_from_directory
from apiflask import Schema, abort
from apiflask.fields import Integer, String, URL, File, Nested, List
from apiflask.validators import Length, OneOf
import traceback
import logging

from deployers.clouds.google_cloud import GoogleCloudManager
from utils.customer_data_platfrom_infrastructure_connect import ConnectToCustomerGCPDataPlatform, ConnectToCustomerAWSDataPlatform, ConnectToCustomerAzureDataPlatform
from utils.customer_secret_manager_operations import CustomerSecretManager
from utils.customer_data_plaform_files_operator import FileManagerandGitOperator
from utils.customer_data_platform_repository_operator import CustomerManagerGitOperator
from utils.customer_data_platform_cicd_finaliser import CustomerDataPlatformCIFinaliser
from utils.customer_secret_manager_sync_update import CustomerSecretManagerSync
from deployers.services.infra_services.a_secret_manager import LocalVault
from deployers.services.infra_services.a_secret_operator import SecretManager
from deployers.services.infra_services.b_cert_manager import CertManager
from deployers.services.infra_services.c_external_dns import ExternalDNS
from deployers.services.infra_services.d_traefik_lb import TraefikIngress
from deployers.services.infra_services.e_idp_sso_manager import idpSsoManager
from deployers.services.infra_services.f_object_storage_operator import PlatformObjectStorage
from deployers.services.infra_services.g_log_collector import PlatformLogCollector
from deployers.services.infra_services.h_services_monitoring import PlatformMonitoring
from deployers.services.infra_services.i_cluster_clearner import Platformk8sCleaner
from deployers.services.data_services.user_console import PlatformUserConsole
from deployers.services.data_services.cicd_workload_runner import Platformk8sGitRunner
from deployers.services.data_services.data_replication import  DataReplicationDeployer
from deployers.services.data_services.data_orchestration import DataOrchestrationDeployer
from deployers.services.data_services.data_governance import DataGovernanceDeployer
from deployers.services.data_services.data_modeling import DataModelingDeployer
from deployers.services.data_services.data_analysis import BIDeployer
from deployers.services.data_services.data_dcdq_meta_collect import DataDCDQMetaCollectDeployer
from werkzeug.utils import safe_join
from utils.mail_handler import MailSender
from app.security import auth

import ipaddress  # Import the ipaddress module for CIDR validation

# Define the schema
class CustomerVaultInputSchema(Schema):
    client_id = String(
        required=False,
        validate=Length(1, 36),
        metadata={'description': 'Fast.BI Vault Master ClientID for authentication.'}
    )
    client_secret = String(
        required=False,
        validate=Length(1, 64),
        metadata={'description': 'Fast.BI Vault Master SecretToken for authentication.'}
    )
    customer = String(
        required=True,
        validate=Length(1, 64),
        metadata={'description': 'Customer tenant name for project identification.'}
    )
    user_email = String(
        required=False,
        validate=Length(1, 64),
        metadata={'description': 'Fast.BI Support Admin email for workspace access.'}
    )
    method = String(
        required=False,
        validate=OneOf(['external_infisical', 'local_vault']),
        metadata={'description': 'Vault method to use. Options: external_infisical (Infisical cloud), local_vault (HashiCorp Vault).'}
    )
    data_analysis_platform = String(
        required=True,
        metadata={'description': 'Data analysis platform to be used (e.g., "lightdash", "metabase", "superset").'}
    )
    data_warehouse_platform = String(
        required=True,
        metadata={'description': 'Data warehouse platform to be used (e.g., "bigquery", "snowflake", "redshift").'}
    )
    git_provider = String(
        required=True,
        metadata={'description': 'Git provider for repositories (e.g., "fastbi", "github", "gitlab", "bitbucket").'}
    )
    dag_repo_url = String(
        required=True,
        metadata={'description': 'URL of the DAG repository for orchestration code.'}
    )
    data_repo_url = String(
        required=True,
        metadata={'description': 'URL of the data repository for data models and transformations.'}
    )
    data_repo_main_branch = String(
        required=False,
        default='master',
        metadata={'description': 'Main branch name for the data repository. Defaults to "master".'}
    )
    repo_access_method = String(
        required=False,
        default='access_token',
        validate=OneOf(['access_token', 'deploy_keys']),
        metadata={'description': 'Method to access repositories. Options: access_token, deploy_keys. Defaults to access_token.'}
    )
    project_id = String(
        required=False,
        metadata={'description': 'Cloud project identifier (e.g., GCP project ID, AWS account ID).'}
    )
    project_region = String(
        required=False,
        metadata={'description': 'Cloud project region (e.g., us-central1, eu-west-1).'}
    )
    cloud_provider = String(
        required=False,
        validate=OneOf(['gcp', 'aws', 'azure']),
        metadata={'description': 'Cloud provider for infrastructure. Options: gcp, aws, azure.'}
    )
    git_provider_access_token = String(
        required=False,
        metadata={'description': 'Access token for Git provider authentication.'}
    )
    private_key_orchestrator = String(
        required=False,
        metadata={'description': 'SSH private key for orchestrator service authentication.'}
    )
    public_key_orchestrator = String(
        required=False,
        metadata={'description': 'SSH public key for orchestrator service authentication.'}
    )
    private_key_data_model = String(
        required=False,
        metadata={'description': 'SSH private key for data model service authentication.'}
    )
    public_key_data_model = String(
        required=False,
        metadata={'description': 'SSH public key for data model service authentication.'}
    )
    smtp_host = String(
        required=False,
        metadata={'description': 'SMTP server hostname for email notifications.'}
    )
    smtp_port = String(
        required=False,
        metadata={'description': 'SMTP server port for email notifications.'}
    )
    smtp_username = String(
        required=False,
        metadata={'description': 'SMTP authentication username.'}
    )
    smtp_password = String(
        required=False,
        metadata={'description': 'SMTP authentication password.'}
    )
    orchestrator_platform = String(
        required=False,
        default='Airflow',
        metadata={'description': 'Orchestration platform to be used. Defaults to "Airflow".'}
    )
    lookersdk_base_url = String(
        required=False,
        metadata={'description': 'Base URL for Looker SDK integration.'}
    )
    lookersdk_client_id = String(
        required=False,
        metadata={'description': 'Client ID for Looker SDK authentication.'}
    )
    lookersdk_client_secret = String(
        required=False,
        metadata={'description': 'Client secret for Looker SDK authentication.'}
    )
class CustomerVaultOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer secrets creation confirmation message.'})
    session_id = String(metadata={'description': 'The unique identifier of the session.'})
    details = String(metadata={'description': 'The Customer secrets creation confirmation detail output.'})

class CustomerInfraDeploymentInputSchema(Schema):
    cloud_provider = String(required=True, default="gcp", validate=OneOf(['gcp', 'aws', 'azure']), metadata={'description': 'The cloud provider for the deployment.'})
    deployment = String(required=True, default="basic", validate=Length(min=1, max=8), metadata={'description': 'The deployment configuration basic/advanced.'})
    billing_account_id = String(required=False, validate=Length(min=1, max=64), metadata={'description': 'The billing account ID. Optional'})
    parent_folder = String(required=False, validate=Length(min=1, max=12), metadata={'description': 'The Customer parent folder ID in GCP Organization. Optional'})
    customer = String(required=True, validate=Length(min=1, max=64), metadata={'description': 'Customer tenant name.'})
    region = String(required=False, validate=Length(min=1, max=64), metadata={'description': 'The region for the deployment. Optional'})
    project_id = String(required=False, validate=Length(min=1, max=64), metadata={'description': 'The project ID for GCP. Auto-Generated'})
    admin_email = String(required=True, validate=Length(min=1, max=64), metadata={'description': 'Fast.BI Support Admin email.'})
    whitelisted_ips = List(String, required=False, validate=Length(min=1, max=19), metadata={'description': 'The whitelisted IPs. Optional'})
class CustomerInfraDeploymentOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer infrastructure deployment confirmation message.'})
    session_id = Integer(metadata={'description': 'The unique identifier of the session.'})
    details = String(metadata={'description': 'The Customer infrastructure deployment confirmation detail output.'})

class InfraServicesAdvancedConfigSchema(Schema):
    traefik_external_ip = String(required=False, validate=Length(1, 16), metadata={'description': 'The Traefik external IP. Optional'})

class CustomerInfraServicesDeploymentInputSchema(Schema):
    secret_manager_type = String(required=False, default="global", validate=OneOf(['global', 'local']), metadata={'description': 'Type of secret manager to use. Either global (Fast.BI) or local (Hashicorp Vault)'})
    vault_chart_version = String(required=False, default="0.29.1", validate=Length(1, 12), metadata={'description': 'The Hashicorp Vault chart version. Required if secret_manager_type is local'})
    user_email = String(required=False, validate=Length(1, 64), metadata={'description': 'Fast.BI Support Admin email.'})
    cloud_provider = String(required=True, default="gcp", validate=OneOf(['gcp', 'aws', 'azure']), metadata={'description': 'The cloud provider for the deployment.'})
    customer = String(required=True, validate=Length(1, 64), metadata={'description': 'Customer tenant name.'})
    region = String(required=False, validate=Length(1, 64), metadata={'description': 'The region for the deployment. Optional'})
    project_id = String(required=False, validate=Length(1, 64), metadata={'description': 'The project ID for GCP. Auto-Generated'})
    external_dns_domain_filters = List(String, required=False, validate=Length(min=1, max=255), metadata={'description': 'The external DNS domain filters. Optional'})
    whitelisted_environment_ips = List(String, required=False, validate=Length(min=1, max=19), metadata={'description': 'The whitelisted IPs. Optional'})
    secret_operator_chart_version = String(required=True, default="0.5.2", validate=Length(1, 12), metadata={'description': 'The Secret Operator chart version. Optional'})
    cert_manager_chart_version = String(required=True, default="v1.15.0", validate=Length(1, 12), metadata={'description': 'The Cert Manager chart version. Optional'})
    external_dns_chart_version = String(required=True, default="7.5.5", validate=Length(1, 12), metadata={'description': 'The External DNS chart version. Optional'})
    traefik_chart_version = String(required=True, default="28.2.0", validate=Length(1, 12), metadata={'description': 'The Traefik chart version. Optional'})
    keycloak_chart_version = String(required=True, default="21.4.1", validate=Length(1, 12), metadata={'description': 'The Keycloak chart version. Optional'})
    object_storage_chart_version = String(required=True, default="5.0.15", validate=Length(1, 12), metadata={'description': 'The Object Storage chart version. Optional'})
    object_storage_operator_chart_version = String(required=True, default="5.0.15", validate=Length(1, 12), metadata={'description': 'The Object Storage Operator chart version. Optional'})
    prometheus_chart_version = String(required=True, default="25.21.0", validate=Length(1, 12), metadata={'description': 'The Prometheus chart version. Optional'})
    grafana_chart_version = String(required=True, default="8.0.1", validate=Length(1, 12), metadata={'description': 'The Grafana chart version. Optional'})
    kube_cleanup_operator_chart_version = String(required=True, default="1.0.4", validate=Length(1, 12), metadata={'description': 'The Kube Cleanup Operator chart version. Optional'})
    advanced_config = Nested(InfraServicesAdvancedConfigSchema, required=False, metadata={'description': 'The advanced configuration. Optional'})

class CustomerInfraServicesDeploymentOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer infrastructure services deployment confirmation message.'})
    session_id = Integer(metadata={'description': 'The unique identifier of the session.'})
    details = String(metadata={'description': 'The Customer infrastructure services deployment confirmation detail output.'})

class CustomerDataServicesDeploymentInputSchema(Schema):
    user_email = String(required=False, validate=Length(1, 64), metadata={'description': 'Fast.BI Support Admin email.'})
    cloud_provider = String(required=True,  default="gcp", validate=OneOf(['gcp', 'aws', 'azure']), metadata={'description': 'The cloud provider for the deployment.'})
    customer = String(required=True, validate=Length(1, 64), metadata={'description': 'Customer tenant name.'})
    region = String(required=False, validate=Length(1, 64), metadata={'description': 'The region for the deployment. Optional'})
    project_id = String(required=False, validate=Length(1, 64), metadata={'description': 'The project ID for GCP. Auto-Generated'})
    git_provider = String(required=True, default="fastbi", validate=OneOf(['fastbi', 'gitlab', 'github', 'bitbucket']), metadata={'description': 'The Git provider for the deployment. Optional'})
    git_url = String(required=False, validate=Length(1, 255), metadata={'description': 'The Git URL for the deployment. Optional'})
    git_runner_token = String(required=False, validate=Length(1, 64), metadata={'description': 'The Git Runner Token for the deployment. Optional'})
    data_replication_default_destination_type = String(required=True, default='bigquery', validate=OneOf(['bigquery', 'snowflake', 'synapse', 'redshift']), metadata={'description': 'The Data Replication default destination type. Optional'})
    tsb_fastbi_web_core_image_version = String(required=True, default="bi-platform/tsb-fastbi-web-core:v0.2.3.0", validate=Length(1, 255), metadata={'description': 'The TSB Fast.BI Web Core image version.'})
    tsb_dbt_init_core_image_version = String(required=True, default="bi-platform/tsb-dbt-init-core:v0.2.6", validate=Length(1, 255), metadata={'description': 'The TSB DBT Init Core image version'})
    gitlab_runner_chart_version = String(required=False, default="0.65.0", validate=Length(1, 12), metadata={'description': 'The GitLab Runner chart version.'})
    airbyte_oss_chart_version = String(required=False, default="0.143.0", validate=Length(1, 12), metadata={'description': 'The Airbyte OSS chart version.'})
    airflow_chart_version = String(required=False, default="1.13.1", validate=Length(1, 12), metadata={'description': 'The Airflow chart version.'})
    airflow_app_version = String(required=False, default="2.8.4", validate=Length(1, 12), metadata={'description': 'The Airflow app version.'})
    datahub_chart_version = String(required=False, default="0.4.16", validate=Length(1, 12), metadata={'description': 'The DataHub chart version.'})
    datahub_prereq_chart_version = String(required=False, default="0.1.10", validate=Length(1, 12), metadata={'description': 'The DataHub Prerequisites chart version.'})
    datahub_eck_es_op_chart_version = String(required=False, default="2.13.0", validate=Length(1, 12), metadata={'description': 'The DataHub ECK ElasticSearch Operator chart version.'})
    datahub_eck_es_chart_version = String(required=False, default="0.11.0", validate=Length(1, 12), metadata={'description': 'The DataHub ECK ElasticSearch chart version.'})
    jupyterhub_chart_version = String(required=False, default="3.3.7", validate=Length(1, 12), metadata={'description': 'The JupyterHub chart version.'})
    jupyterhub_app_version = String(required=False, default="v4.22.1-focal", validate=Length(1, 32), metadata={'description': 'The JupyterHub app version.'})
    bi_system = String(required=True, default='lightdash', validate=(Length(1, 12),OneOf(['lightdash', 'superset', 'metabase', 'looker'])), metadata={'description': 'The BI System.'})
    superset_chart_version = String(required=False, default="0.12.11", validate=Length(1, 12), metadata={'description': 'The Superset chart version.'})
    superset_app_version = String(required=False, validate=Length(1, 12), metadata={'description': 'The Superset app version.'})
    lightdash_chart_version = String(required=False, default="0.9.0", validate=Length(1, 12), metadata={'description': 'The Lightdash chart version.'})
    lightdash_app_version = String(required=False, validate=Length(1, 12), metadata={'description': 'The Lightdash app version.'})
    metabase_chart_version = String(required=False, default="2.15.7", validate=Length(1, 12), metadata={'description': 'The Metabase chart version.'})
    metabase_app_version = String(required=False, validate=Length(1, 12), metadata={'description': 'The Metabase app version.'})
    external_looker = String(required=False, validate=Length(1, 12), metadata={'description': 'The Looker chart version. Optional'})
    dcdq_metacollect_chart_version = String(required=False, default="Empty", validate=Length(1, 12), metadata={'description': 'The DCDQ MetaCollect chart version.'})
    dcdq_metacollect_app_version = String(required=False, default="bi-platform/tsb-fastbi-meta-api-core:v1.0.0", validate=Length(1, 255), metadata={'description': 'The DCDQ MetaCollect app version.'})
class CustomerDataServicesDeploymentOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer data services deployment confirmation message.'})
    session_id = Integer(metadata={'description': 'The unique identifier of the session.'})
    details = String(metadata={'description': 'The Customer data services deployment confirmation detail output.'})

class CustomerDataRepoServicesDeploymentInputSchema(Schema):
    customer = String(required=True, validate=Length(1, 64), metadata={'description': 'Customer tenant name.'})
    project_id = String(required=False, validate=Length(1, 64), metadata={'description': 'The project ID for GCP. Auto-Generated'})
    git_provider = String(required=True, validate=OneOf(['fastbi', 'gitlab', 'github', 'bitbucket']), metadata={'description': 'The Git provider for the deployment.'})
    fast_bi_cicd_version = String(required=False, validate=Length(1, 12), metadata={'description': 'The Fast.BI CICD version. Optional'})
    git_access_token = String(required=False, validate=Length(1, 64), metadata={'description': 'The Git Access Token for the deployment. Optional'})
class CustomerDataRepoServicesDeploymentOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer data repo services deployment confirmation message.'})
    session_id = Integer(metadata={'description': 'The unique identifier of the session.'})
    details = String(metadata={'description': 'The Customer data repo services deployment confirmation detail output.'})

class CustomerRealmDownloadOutputSchema(Schema):
    output = File(metadata={'description': 'The Customer realm json file.'})

class CustomerRealmGetInfoInputSchema(Schema):
    customer = String(required=True, validate=Length(1, 64), metadata={'description': 'Customer tenant name.'})
class CustomerRealmGetInfoOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer realm info confirmation message.'})
    customer = String(metadata={'description': 'Customer tenant name.'})
    realm_configuration_file_url = URL(metadata={'description': 'The Customer realm configuration file URL.'})
    customer_idp_sso_credentials_url = URL(metadata={'description': 'The Customer IDP SSO credentials URL.'})
    idp_console_endpoint_url = URL(metadata={'description': 'The IDP Console endpoint URL.'})

class CustomerCredentialsRetrieveOutputSchema(Schema):
    credentials = String(metadata={'description': 'The Customer credentials in JSON format.'})

class CustomerDeploymentFilesSaveInputSchema(Schema):
    cloud_provider = String(required=True, validate=OneOf(['gcp', 'aws', 'azure']), metadata={'description': 'The cloud provider for the deployment.'})
    customer = String(required=True, validate=Length(1, 64), metadata={'description': 'Customer tenant name.'})
    git_access_token = String(required=False, validate=Length(1, 64), metadata={'description': 'The Git Access Token for the deployment. Optional'})
    user_email = String(required=False, validate=Length(1, 64), metadata={'description': 'Fast.BI Support Admin email.'})
class CustomerDeploymentFilesSaveDetailOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer deployment files Confirmation output message.'})
    details = String(metadata={'description': 'The Customer deployment files save detail output.'})
    realm_download_url = URL(metadata={'description': 'The Customer realm download URL.'})
    token_url = URL(metadata={'description': 'The Customer token URL.'})
    decryption_key = String(metadata={'description': 'The Customer decryption key.'})
    customer_file_manager_operator_repo_link = URL(metadata={'description': 'The Customer file manager operator repo link.'})
class CustomerDeploymentFilesSaveOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer deployment files save confirmation message.'})
    details = Nested(CustomerDeploymentFilesSaveDetailOutputSchema, metadata={'description': 'The Customer deployment files save confirmation detail output.'})

class CustomerDataRepoCIFinaliserDeploymentInputSchema(Schema):
    cloud_provider = String(required=True, validate=OneOf(['gcp', 'aws', 'azure']), metadata={'description': 'The cloud provider for the deployment.'})
    customer = String(required=True, validate=Length(1, 64), metadata={'description': 'Customer tenant name.'})
    project_id = String(required=False, validate=Length(1, 64), metadata={'description': 'The project ID for GCP. Auto-Generated'})
    git_provider = String(required=True, validate=OneOf(['fastbi', 'gitlab', 'github', 'bitbucket']), metadata={'description': 'The Git provider for the deployment.'})
    git_access_token = String(required=False, validate=Length(1, 64), metadata={'description': 'The Data Repository Access Token'})
    bi_system = String(required=True, default='lightdash', validate=(Length(1, 12),OneOf(['lightdash', 'superset', 'metabase', 'looker'])), metadata={'description': 'The BI System.'})
    data_orchestrator_platform = String(required=True, default='Airflow', validate=(Length(1, 12),OneOf(['Airflow', 'Composer'])), metadata={'description': 'The Data Orchestrator Platform.'})
class CustomerDataRepoCIFinaliserDeploymentOutputSchema(Schema):
    message = String(metadata={'description': 'The Customer data repo CI finaliser deployment confirmation message.'})
    session_id = Integer(metadata={'description': 'The unique identifier of the session.'})
    details = String(metadata={'description': 'The Customer data repo CI finaliser deployment confirmation detail output.'})

logger = logging.getLogger(__name__)

def validate_and_format_ips(ip_list):
    formatted_ips = []
    for ip in ip_list:
        try:
            # Validate and convert to CIDR format
            ip_obj = ipaddress.ip_network(ip.strip(), strict=False)
            formatted_ips.append(str(ip_obj))
        except ValueError:
            logger.error(f"Invalid IP/CIDR format: {ip.strip()}")
            continue  # Skip invalid entries
    return formatted_ips

def setup_routes(app):
    # Define the routes
    @app.get('/')
    @app.doc(tags=['Health'])
    def say_hello():
        """Just Say Hello

        It will always return a greeting like this:
        ```
        {'message': 'Hello! I'm API Fast.BI Customer Tenant Deployer. I'm alive!', 'url': '/docs'}
        ```
        """
        return {"message": "Hello! I'm API Fast.BI Customer Tenant Deployer. I'm alive!", "url": "/docs"}, 200

    @app.route('/admin/logs')
    @app.auth_required(auth)
    @app.doc(tags=['Health'])
    def download_logs():
        # Use an absolute path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(base_dir, 'logs', 'app.log')
        
        current_app.logger.debug(f"Current working directory: {os.getcwd()}")
        current_app.logger.debug(f"Base directory: {base_dir}")
        current_app.logger.debug(f"Attempting to access log file at: {log_file}")
        
        if os.path.exists(log_file):
            current_app.logger.info(f"Log file found, sending: {log_file}")
            return send_file(log_file, as_attachment=True)
        else:
            current_app.logger.warning(f"Log file not found at: {log_file}")
            # List contents of the logs directory
            logs_dir = os.path.dirname(log_file)
            if os.path.exists(logs_dir):
                current_app.logger.debug(f"Contents of {logs_dir}: {os.listdir(logs_dir)}")
            else:
                current_app.logger.warning(f"Logs directory not found: {logs_dir}")
            abort(404, message="Log file not found")

    @app.route('/admin/latest_services_versions')
    @app.auth_required(auth)
    @app.doc(tags=['Health'])
    def latest_chart_services_versions():
        # Database Connection:
        metadata_collector = current_app.metadata_collector
        
        # Trigger fetch latest versions by helm chart.
        get_latest_versions = current_app.latest_services_versions()
        
        # Update the database record for previous latest status
        current_latests_version_updates = metadata_collector.update_current_helm_chart_service_versions()
        
        if current_latests_version_updates:
            # Insert new versions to the database
            latests_version_updates = metadata_collector.insert_latest_helm_chart_service_versions(get_latest_versions)
            
            if latests_version_updates:
                # Delete versions older than 9 months
                metadata_collector.delete_old_versions()
                
                # Retrieve the latest versions from the database
                db_latest_versions = metadata_collector.get_latest_versions()
                
                if db_latest_versions is not None:
                    # Remove empty categories
                    db_latest_versions = {k: v for k, v in db_latest_versions.items() if v}
                    
                    response_message = {
                        "message": "Helm chart versions updated successfully",
                        "details": db_latest_versions
                    }
                    return jsonify(response_message), 200
                else:
                    response_message = {
                        "message": "Failed to retrieve latest versions from database",
                        "details": None
                    }
                    return jsonify(response_message), 500
            else:
                response_message = {
                    "message": "Failed to insert latest versions",
                    "details": None
                }
                return jsonify(response_message), 500
        else:
            response_message = {
                "message": "Failed to update current versions",
                "details": None
            }
            return jsonify(response_message), 500

    #Init Customer - prepare secrets
    @app.route('/create-customer-vault', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-Vault'])
    @app.input(CustomerVaultInputSchema, location='json')
    @app.output(CustomerVaultOutputSchema)
    def create_customer_vault(json_data):
        stage_id = '1'
        stage = "vault"
        
        # Get values from json_data with fallbacks to config
        processed_data = {
            'client_id': json_data.get('client_id', current_app.config['FASTBI_VAULT_CLIENT_ID']),
            'client_secret': json_data.get('client_secret', current_app.config['FASTBI_VAULT_CLIENT_SECRET']),
            'project_name': json_data.get('customer'),
            'user_email': json_data.get('user_email', current_app.config['FASTBI_ADMIN_EMAIL']),
            'method': json_data.get('method', 'external_infisical'),
            'customer': json_data.get('customer'),
            'data_analysis_platform': json_data.get('data_analysis_platform'),
            'data_warehouse_platform': json_data.get('data_warehouse_platform'),
            'git_provider': json_data.get('git_provider'),
            'dag_repo_url': json_data.get('dag_repo_url'),
            'data_repo_url': json_data.get('data_repo_url'),
            # Optional parameters with defaults
            'data_repo_main_branch': json_data.get('data_repo_main_branch', 'master'),
            'repo_access_method': json_data.get('repo_access_method', 'access_token'),
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
            'orchestrator_platform': json_data.get('orchestrator_platform', 'Airflow'),
            'lookersdk_base_url': json_data.get('lookersdk_base_url'),
            'lookersdk_client_id': json_data.get('lookersdk_client_id'),
            'lookersdk_client_secret': json_data.get('lookersdk_client_secret')
        }

        try:
            # Create manager instance using the API factory method
            manager = CustomerSecretManager.from_api_request(processed_data)
            results = manager.run()
            
            if results['status'] == 'success':
                details = "OK"
            else:
                details = "Empty"

            deployment_result = {
                "message": "Customer secrets initiated successfully",
                "details": results
            }

            # Save deployment and session data
            metadata_collector = current_app.metadata_collector
            if metadata_collector is None:
                return {"error": "Metadata collector not initialized"}, 500
            
            try:
                session_id = metadata_collector.save_session_data(
                    processed_data['customer'], 
                    stage_id, 
                    stage, 
                    deployment_result
                )
            except Exception as e:
                return {"error": str(e)}, 500
                
            return {
                "message": "Customer secrets initiated successfully",
                "session_id": session_id,
                "details": details
            }, 200
            
        except Exception as e:
            return {"error": str(e)}, 500

    ###Customer cloud data-platform
    # Download Keycloak customer realm file
    @app.route('/deploy/realm/download/<customer>')
    #@app.auth_required(auth)
    @app.doc(tags=['Customer-Tenant-Metadata'])
    @app.output(CustomerRealmDownloadOutputSchema, status_code=200)
    def download_realm(customer):
        base_dir = os.path.dirname(__file__)  # Gets the directory where this script is located
        parent_dir = os.path.join(base_dir, os.pardir)  # Navigate to the parent directory of `base_dir`
        directory = os.path.abspath(os.path.join(parent_dir, 'charts/infra_services_charts/idp_sso_manager/'))
        filepath = safe_join(directory, f"{customer}_realm.json")
        if not os.path.exists(filepath):
            abort(404)
        return send_from_directory(directory, f"{customer}_realm.json", as_attachment=True)

    @app.route('/retrieve-credentials/<token>')
    #@app.auth_required(auth)
    @app.doc(tags=['Customer-Tenant-Metadata'])
    def retrieve_credentials(token):
        credentials = current_app.cache.get(token)
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title }}</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f0f0f0;
                }
                .container {
                    text-align: center;
                    background-color: white;
                    padding: 2rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    max-width: 80%;
                }
                h1 {
                    color: #4a6bff;
                    margin-bottom: 1rem;
                }
                p {
                    color: #333;
                    margin-bottom: 1rem;
                }
                .credentials {
                    background-color: #f5f5f5;
                    padding: 1rem;
                    border-radius: 4px;
                    text-align: left;
                    margin-bottom: 1rem;
                }
                .credential-item {
                    margin-bottom: 0.5rem;
                }
                .credential-label {
                    font-weight: bold;
                }
                .close-button {
                    background-color: #6788ff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    text-align: center;
                    text-decoration: none;
                    display: inline-block;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 4px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{{ heading }}</h1>
                <p>{{ message }}</p>
                {% if show_credentials %}
                <div class="credentials">
                    <div class="credential-item">
                        <span class="credential-label">Username:</span> {{ username }}
                    </div>
                    <div class="credential-item">
                        <span class="credential-label">Password:</span> {{ password }}
                    </div>
                </div>
                {% endif %}
                <button class="close-button" onclick="window.close()">Close Window</button>
            </div>

            {% if show_credentials %}
            <script>
                if (window.opener) {
                    window.opener.postMessage({ status: "success", message: "Credentials retrieved successfully" }, '*');
                }
            </script>
            {% endif %}
        </body>
        </html>
        """

        if credentials:
            try:
                cred_dict = json.loads(credentials) if isinstance(credentials, str) else credentials
                username = cred_dict.get('username', 'N/A')
                password = cred_dict.get('password', 'N/A')
                return render_template_string(
                    html_template,
                    title="Credentials Retrieved",
                    heading="Credentials Retrieved Successfully",
                    message="Here are your credentials:",
                    show_credentials=True,
                    username=username,
                    password=password
                )
            except json.JSONDecodeError:
                return render_template_string(
                    html_template,
                    title="Error Parsing Credentials",
                    heading="Error Parsing Credentials",
                    message="Unable to parse the retrieved credentials.",
                    show_credentials=False
                ), 500
        else:
            return render_template_string(
                html_template,
                title="Credentials Not Found",
                heading="Credentials Not Found",
                message="The credentials you're looking for have already been retrieved, expired, or never existed.",
                show_credentials=False
            ), 404

    # Upload Customer infrastructure and Data Service Deployment files to Repo.
    @app.route('/deploy/deployment-files-save', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-Tenant-Metadata'])
    @app.input(CustomerDeploymentFilesSaveInputSchema, location='json')
    @app.output(CustomerDeploymentFilesSaveOutputSchema, status_code=200)
    def deployment_files_save(json_data):
        data = json_data
        cloud_provider = data.get('cloud_provider')
        customer = data.get('customer')
        git_access_token = data.get('git_access_token', None) or current_app.config['GITLAB_ADMIN_ACCESS_TOKEN']
        user_email = data.get('user_email') or data.get('admin_email') or current_app.config['FASTBI_ADMIN_EMAIL']
        try:
            metadata_collector = current_app.metadata_collector
            vault_session_data = metadata_collector.retrieve_session_data(customer, "1")
            if not vault_session_data:
                return {"error": "Vault session data not found for customer"}, 404
            infrastructure_session_data = metadata_collector.retrieve_session_data(customer, "2")
            if not infrastructure_session_data:
                return {"error": "Infrastructure deployment session data not found for customer"}, 404
            k8s_infrastructure_services_session_data = metadata_collector.retrieve_session_data(customer, "3")
            if not k8s_infrastructure_services_session_data:
                return {"error": "K8s Infrastructure services deployment session data not found for customer"}, 404
            
            customer_vault_deployment_details = vault_session_data['message']
            customer_infrastructure_deployment_details = infrastructure_session_data['message']
            customer_k8s_infrastructure_services_deployment_details = k8s_infrastructure_services_session_data['message'] + '\n'.join(k8s_infrastructure_services_session_data['details'])

            deployment_details = {
                "vault": {"status": customer_vault_deployment_details},
                "infrastructure": {"status": customer_infrastructure_deployment_details},
                "k8s_infrastructure_services": {"status": "Main Infra services successfully deployed",
                                                "details": customer_k8s_infrastructure_services_deployment_details}
            }


            vault_project_id = vault_session_data['details']['project_id']
            secret_manager_client_id = vault_session_data['details']['client_id']
            secret_manager_client_secret = vault_session_data['details']['client_secret']

            customer_file_manager_operator = FileManagerandGitOperator(
            cloud_provider = cloud_provider,
            vault_project_id=vault_project_id, 
            secret_manager_client_id=secret_manager_client_id, 
            secret_manager_client_secret=secret_manager_client_secret, 
            customer=customer, 
            access_token=git_access_token
            )
            customer_file_manager_operator_message = customer_file_manager_operator.setup_and_push_files()
            customer_file_manager_operator_decryption_key = customer_file_manager_operator.get_encryption_key()

            download_url = k8s_infrastructure_services_session_data['realm_download_url']

            token_url = k8s_infrastructure_services_session_data['token_url']

            response_details = {
                "message": "Main Infra services successfully deployed",
                "details": deployment_details,
                "realm_download_url": download_url,
                "token_url": token_url,
                "decryption_key": customer_file_manager_operator_decryption_key,
                "customer_file_manager_operator_repo_link": customer_file_manager_operator_message['customer_root_url']
            }

            # Send email if user was provided
            if user_email:
                mail_sender = MailSender(current_app)
                subject = "Fast.BI Deployment Details"
                logo_url = "https://wiki.fast.bi/logo_transparent_original.png"
                details_formatted = '<ul>'
                if isinstance(response_details['details'], dict):
                    for key, value in response_details['details'].items():
                        details_formatted += f'<li><b>{key}:</b>'
                        details_formatted += f'<ul><li>Status: {value["status"]}</li>'
                        if isinstance(value.get('details'), str):
                            details_formatted += '<li>Details:<ul>'
                            if value['details'].startswith(value["status"]):
                                # If the details start with the status, remove the status line
                                details = value['details'][len(value["status"]):].strip()
                                # Ensure details is not empty after removing the status
                                if details:
                                    for line in details.split('\n'):
                                        details_formatted += f'<li>{line.strip()}</li>'
                            else:
                                # If the details do not start with the status, include them as is
                                for line in value['details'].split('\n'):
                                    details_formatted += f'<li>{line.strip()}</li>'
                            details_formatted += '</ul></li>'
                        details_formatted += '</ul></li>'
                else:
                    # If it's not a dictionary, just include the string value
                    details_formatted += f'<li>{response_details["details"]}</li>'
                body = f"""
                <html>
                    <head></head>
                    <body>
                        <h1>Fast.BI Deployment Details</h1>
                        <img src="{logo_url}" alt="Fast.BI Logo" style="width:200px;">
                        <p>Fast.BI infrastructure services were successfully deployed for {customer} tenant.</p>
                        <h2>Deployment Details:</h2>
                        {details_formatted}
                        <p>Download your configuration realm file <a href="{response_details['realm_download_url']}">here</a>.</p>
                        <p>Retrieve your credentials for idp-sso-manager-ui <a href="{response_details['token_url']}">here</a>.</p>
                        <p>Customer Infrastructure deployment files are available in your repository <a href="{response_details['customer_file_manager_operator_repo_link']}">here</a>.</p>
                        <p>Decryption key for your infrasructure deployment files: {response_details['decryption_key']}</p>
                        <p>Thank you for using Fast.BI.</p>
                    </body>
                </html>
                """
                mail_sender.send_email(subject, body, user_email)

            # Process session data to save deployment files, etc.
            #result = finalize_deployment(session_data)

            return {"message": "New tenant was issued successfully", "details": response_details}, 200
        except Exception as e:
            return {"error": str(e)}, 500


    @app.route('/deploy/infra-environment', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-Ifrastructure'])
    @app.input(CustomerInfraDeploymentInputSchema, location='json')
    @app.output(CustomerInfraDeploymentOutputSchema, status_code=200)
    def deploy_infra_environment(json_data):
        stage_id = '2'
        stage = "infrasructure_deployment"
        try:
            logger.info("Starting infrastructure deployment")
            cloud_provider = json_data.get('cloud_provider')
            
            if cloud_provider not in ['gcp', 'aws', 'azure']:
                logger.error(f"Unsupported cloud provider: {cloud_provider}")
                return {"error": f"{cloud_provider} deployment not supported or invalid"}, 400

            if cloud_provider == 'gcp':
                # Gather all parameters
                deployment = json_data.get('deployment')
                billing_account_id = json_data.get('billing_account_id')
                parent_folder = json_data.get('parent_folder')
                customer = json_data.get('customer')
                region = json_data.get('region')
                project_id = json_data.get('project_id')
                admin_email = json_data.get('admin_email')
                whitelisted_ips = json_data.get('whitelisted_ips')

                # Optional advanced configuration
                advanced_config = {
                    "cidr_block": json_data.get('cidr_block'),
                    "cluster_ipv4_cidr_block": json_data.get('cluster_ipv4_cidr_block'),
                    "services_ipv4_cidr_block": json_data.get('services_ipv4_cidr_block'),
                    "private_service_connect_cidr": json_data.get('private_service_connect_cidr'),
                    "lb_subnet_cidr": json_data.get('lb_subnet_cidr'),
                    "shared_host": json_data.get('shared_host'),
                    "kubernetes_version": json_data.get('kubernetes_version'),
                    "gke_machine_type": json_data.get('gke_machine_type'),
                    "gke_spot": json_data.get('gke_spot'),
                    "k8s_master_ipv4_cidr_block": json_data.get('k8s_master_ipv4_cidr_block')
                }

                # Get the token key from the header
                token_key = request.headers.get('X-Token-Key')
                
                if not token_key:
                    return jsonify({"error": "X-Token-Key header is required"}), 400

                # Fetch the access token from the database
                metadata_collector = current_app.metadata_collector
                token_data = metadata_collector.get_access_token(token_key)

                if not token_data:
                    return jsonify({"error": "Invalid or expired token key"}), 401
                logger.info(f"Access token retrieved: {'Yes' if token_data else 'No'}")

                access_token, refresh_token, token_expiry = token_data

                # If access_token is not available, try to get service account key
                if not access_token:
                    # You need to implement a way to securely retrieve the service account key
                    # This is just a placeholder - replace with your actual method
                    # TODO: Right now not in the scope - future task
                    # service_account_key = get_service_account_key()
                    service_account_key = None
                    logger.info(f"Service account key retrieved: {'Yes' if service_account_key else 'No'}")
                else:
                    service_account_key = None

                if not access_token and not service_account_key:
                    logger.error("No authentication method available")
                    return {"error": "No authentication method available"}, 401

                logger.info("Creating GoogleCloudManager instance")
                manager = GoogleCloudManager(
                    deployment=deployment,
                    billing_account_id=billing_account_id,
                    parent_folder=parent_folder,
                    customer=customer,
                    admin_email=admin_email,
                    whitelisted_ips=whitelisted_ips,
                    region=region,
                    project_id=project_id,
                    cloud_provider=cloud_provider,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expiry=token_expiry,
                    token_key=token_key,
                    service_account_key=service_account_key,
                    **advanced_config
                )

                # Render configuration files and deploy
                logger.info("Rendering configuration files")
                manager.render_backend_tf()
                manager.render_defaults_yaml()
                manager.render_env_yaml()
                manager.render_terragrunt_hcl()
                
                logger.info("Deploying GCP Terragrunt")
                results = manager.deploy_gcp_terragrunt()

                if results['status'] == 'success':
                    details = "OK"
                else:
                    details = "Empty"

                deployment_result = {
                    "message": "Main Infrastructure successfully deployed",
                    "details": results
                }

                # Save deployment and session data
                logger.info("Saving deployment and session data")
                metadata_collector = current_app.metadata_collector
                session_id = metadata_collector.save_session_data(customer, stage_id, stage, deployment_result)
                logger.info("Deployment completed successfully")
                # TODO: Return a link to download the deployment log file.
                return {"message": "Main Infrastructure successfully deployed", "session_id": session_id, "details": details}, 200
            elif cloud_provider == 'aws':
                logger.error("AWS deployment not supported yet")
                return {"error": "AWS deployment - coming soon!"}, 400
            elif cloud_provider == 'azure':
                logger.error("Azure deployment not supported yet")
                return {"error": "Azure deployment - coming soon!"}, 400
        except Exception as e:
            logger.error(f"An error occurred during deployment: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": f"An unexpected error occurred: {str(e)}"}, 500


    @app.route('/deploy/infra-services', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-K8s-InfraServices'])
    @app.input(CustomerInfraServicesDeploymentInputSchema, location='json')
    @app.output(CustomerInfraServicesDeploymentOutputSchema, status_code=200)
    def deploy_infra_services(json_data):
        logger.info("Received request to deploy infra services.")

        stage_id = '3'
        stage = "k8s_infrasructure_services_deployment"
        
        if request.is_json:
            data = json_data
        else:
            logger.error("Invalid or no JSON received.")
            return {"error": "Invalid or no JSON received"}, 400

        try:
            logger.debug("Parsing JSON data.")
            secret_manager_type = data.get('secret_manager_type', 'global')

            chart_versions = {}

            if secret_manager_type == 'local':
                chart_versions['vault'] = data.get('vault_chart_version')
            # Extract chart versions

            chart_versions.update({
                'secret_operator': data.get('secret_operator_chart_version'),
                'cert_manager': data.get('cert_manager_chart_version'),
                'external_dns': data.get('external_dns_chart_version'),
                'traefik': data.get('traefik_chart_version'),
                'keycloak': data.get('keycloak_chart_version'),
                'object_storage': data.get('object_storage_chart_version'),
                'object_storage_operator': data.get('object_storage_operator_chart_version'),
                'prometheus': data.get('prometheus_chart_version'),
                'grafana': data.get('grafana_chart_version'),
                'kube_cleanup': data.get('kube_cleanup_operator_chart_version')
            })

            logger.debug(f"Chart versions extracted: {chart_versions}")

            customer = data.get('customer', 'demo')
            project_id = data.get('project_id')
            region = data.get('region')
            cloud_provider = data.get('cloud_provider', 'gcp')
            external_dns_domain_filters = data.get('external_dns_domain_filters')
            whitelisted_environment_ips = data.get('whitelisted_environment_ips', [])
            if isinstance(whitelisted_environment_ips, list):
                # If it's already a list, use it directly
                ip_list = whitelisted_environment_ips
            else:
                logger.error("Invalid format for whitelisted_environment_ips. Expected a list.")
                ip_list = []  # Default to an empty list if the format is incorrect
            # Validate the IPs
            whitelisted_environment_ips = validate_and_format_ips(ip_list)
            logger.debug(f"Whitelisted Environment IPs: {whitelisted_environment_ips}")

            # Extract advanced config
            advanced_config = json_data.get('advanced_config')
            traefik_external_ip = None  # Initialize the variable
            if advanced_config:
                logger.debug(f"Advanced config extracted: {advanced_config}")
                traefik_external_ip = advanced_config.get('traefik_external_ip')  # Assign if exists
                if traefik_external_ip:
                    logger.debug(f"Traefik config extracted: {traefik_external_ip}")
            else:
                logger.debug("No advanced config provided.")

            logger.info(f"Deploying Infra Services for {customer} in {region} project {project_id}")

            # Retrieve customer variables from database
            metadata_collector = current_app.metadata_collector
            vault_session_data = metadata_collector.retrieve_session_data(customer, "1")
            if not vault_session_data:
                logger.error("Vault session data not found for customer.")
                return {"error": "Vault session data not found for customer"}, 404

            slug = vault_session_data['details']['slug']
            vault_project_id = vault_session_data['details']['project_id']
            secret_manager_client_id = vault_session_data['details']['client_id']
            secret_manager_client_secret = vault_session_data['details']['client_secret']

            logger.debug(f"Customer: {customer}")
            logger.debug(f"Slug: {slug}")
            logger.debug(f"Vault Project ID: {vault_project_id}")
            logger.debug(f"Secret Manager Client ID: {secret_manager_client_id}")
            #logger.debug(f"Secret Manager Client Secret: {secret_manager_client_secret}")

            # Connect to Cloud provider data-platform (gcp, aws, azure)
            logger.info(f"Cloud Provider: {cloud_provider}, connecting.")
            try:
                if cloud_provider == "gcp":
                    # Get external ip for traefik
                    ext_ip_name = f"fast-bi-{customer}-traefik-ext-ip"
                    # Get the token key from the header
                    token_key = request.headers.get('X-Token-Key')
                    if not token_key:
                        logger.error("X-Token-Key header is missing")
                        return {"error": "X-Token-Key header is required"}, 400
                    # Fetch the access token using the token key
                    token_data = metadata_collector.get_access_token(token_key)
                    if not token_data:
                        logger.error("Invalid or expired token key")
                        return {"error": "Invalid or expired token key"}, 401
                    
                    access_token, refresh_token, token_expiry = token_data

                    gcm = ConnectToCustomerGCPDataPlatform(
                        customer=customer,
                        project_id=project_id,
                        region=region,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expiry=token_expiry,
                        token_key=token_key
                    )
                    try:
                        gcm.get_kubernetes_credentials()
                        if gcm.test_kubernetes_connection():
                            logger.info("Successfully connected to GKE cluster")
                            if traefik_external_ip:
                                external_ip = traefik_external_ip
                                logger.info(f"Using provided Traefik external IP from advanced config: {external_ip}")
                            else:
                                external_ip = gcm.fetch_external_ip(ext_ip_name)
                                logger.debug(f"External Data Platform IP: {external_ip}")
                        else:
                            raise Exception("Failed to connect to Kubernetes cluster")
                    except Exception as e:
                        logger.error(f"Failed to connect to GKE cluster: {str(e)}")
                        return {"error": f"Failed to connect to GKE cluster: {str(e)}"}, 500
                elif cloud_provider == "aws":
                    acm = ConnectToCustomerAWSDataPlatform(customer=customer, project_id=project_id, region=region)
                    acm.get_kubernetes_credentials()
                elif cloud_provider == "azure":
                    acm = ConnectToCustomerAzureDataPlatform(customer=customer, project_id=project_id, region=region)
                    acm.get_kubernetes_credentials()
                else:
                    raise ValueError("Invalid or not supported cloud provider. Supported cloud providers are: gcp, aws, azure")
                logger.info("Connected to cloud provider successfully.")
            except Exception as cloud_exc:
                logger.error(f"Error connecting to cloud provider: {cloud_exc}", exc_info=True)
                return {"error": str(cloud_exc)}, 500

            logger.info("Starting deployment of infra services.")

            services = {}

            if secret_manager_type == 'local':
                services["0. Local Vault"] = LocalVault(
                    chart_version=chart_versions['vault'],
                    customer=customer,
                    project_id=project_id,
                    slug=slug,
                    metadata_collector=metadata_collector
                )

            services.update({
                "1. Secret Operator": SecretManager(chart_version=chart_versions['secret_operator'], customer=customer, slug=slug, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector),
                "2. Cert Manager": CertManager(chart_version=chart_versions['cert_manager'], customer=customer, project_id=project_id, slug=slug, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector),
                "3. External DNS": ExternalDNS(chart_version=chart_versions['external_dns'], customer=customer, project_id=project_id, slug=slug, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, external_dns_domain_filters=external_dns_domain_filters, metadata_collector=metadata_collector),
                "4. Traefik Ingress": TraefikIngress(chart_version=chart_versions['traefik'], customer=customer, project_id=project_id, region=region, slug=slug, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, whitelisted_environment_ips=whitelisted_environment_ips, external_ip=external_ip, metadata_collector=metadata_collector),
                "5. IDP SSO Manager": idpSsoManager(chart_version=chart_versions['keycloak'], customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector),
                "6. Object Storage": PlatformObjectStorage(chart_version=chart_versions['object_storage'], operator_chart_version=chart_versions['object_storage_operator'], customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector),
                "7. Log Collector": PlatformLogCollector(chart_version=chart_versions['prometheus'], customer=customer, cloud_provider=cloud_provider, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector),
                "8. Platform Monitoring": PlatformMonitoring(chart_version=chart_versions['grafana'], customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector),
                "9. K8s Cleanup": Platformk8sCleaner(chart_version=chart_versions['kube_cleanup'], customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector)
            })

            # Sequential deployment considering dependencies
            results = []
            idp_sso_response = None
            try:
                for name, service in services.items():
                    logger.info(f"Starting deployment of {name}.")
                    if name == "5. IDP SSO Manager":
                        idp_sso_response = service.run()
                        results.append(idp_sso_response["message"])
                    else:
                        result = service.run()
                        logger.info(f"{name} deployed successfully.")
                        results.append(result)
            except Exception as e:
                logger.error(f"Error deploying service {name}: {e}", exc_info=True)
                return {"error": f"Failed to deploy {name}: {str(e)}"}, 500

            # Check if there are any error messages in the results
            error_present = any("error" in result.lower() or "failed" in result.lower() for result in results)
            if not error_present:
                # Extract and sanitize the base URL
                base_url = request.host_url.rstrip('/')
                # Define the expected API path
                api_path = '/api/v1'
                # Check if the base URL already contains the API path
                if not base_url.endswith(api_path):
                    base_url = base_url + api_path
                download_url = f"{base_url}/deploy/realm/download/{customer}"
                token_url = None

                if idp_sso_response and "token" in idp_sso_response:
                    token_url = f"{base_url}/retrieve-credentials/{idp_sso_response['token']}"

                details = "OK" if results else "Empty"

                # Send the response to the front app
                deployment_result = {
                    "message": "Main Infra services successfully deployed",
                    "details": results,
                    "realm_download_url": download_url,
                    "token_url": token_url
                }

                # Save deployment and session data
                session_id = metadata_collector.save_session_data(customer, stage_id, stage, deployment_result)
                logger.info("Infra services deployment completed successfully.")
                return {"message": "Main Infra services successfully deployed", "session_id": session_id, "details": details}, 200
            else:
                logger.error("Deployment failed in one or more components.")
                return {
                    "message": "Deployment failed in one or more components",
                    "details": results
                }, 500

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {"error": str(e)}, 500

    #Deploy Fast.BI main infra platform services.
    @app.route('/get/idp-sso-realm', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-Tenant-Metadata'])
    @app.input(CustomerRealmGetInfoInputSchema, location='json')
    @app.output(CustomerRealmGetInfoOutputSchema, status_code=200)
    def deploy_infra_realm_link_url(json_data):
        customer = json_data.get('customer')
        if not customer:
            return {"error": "Customer parameter is required"}, 400
        try:
            metadata_collector = current_app.metadata_collector
            k8s_infrastructure_services_session_data = metadata_collector.retrieve_session_data(customer, "3")
            if not k8s_infrastructure_services_session_data:
                return {"error": "K8s Infrastructure services deployment session data not found for customer"}, 404

            download_url = k8s_infrastructure_services_session_data.get('realm_download_url')
            token_url = k8s_infrastructure_services_session_data.get('token_url')
            idp_link = f"https://login.{customer}.fast.bi/"
            return {
                "message": "Download the Fast.BI Realm configuration file, open your IDP SSO console, root username and password you can get from 'Customer IDP SSO Credentials'. Configure your new Fast.BI Realm",
                "customer": customer,
                "realm_configuration_file_url": download_url,
                "customer_idp_sso_credentials_url": token_url,
                "idp_console_endpoint_url": idp_link
            }
        except Exception as e:
            return {"error": str(e)}, 500

    @app.route('/deploy/data-services', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-K8s-DataServices'])
    @app.input(CustomerDataServicesDeploymentInputSchema, location='json')
    @app.output(CustomerDataServicesDeploymentOutputSchema, status_code=200)
    def deploy_data_services(json_data):
        stage_id = '5'
        stage = "k8s_data_services_deployment"
        logger = current_app.logger

        if request.is_json:
            data = json_data
        else:
            return {"error": "Invalid or no JSON received"}, 400

        try:
            data_replication_default_destination_type = data.get('data_replication_default_destination_type')
            tsb_fastbi_web_core_image_version = data.get('tsb_fastbi_web_core_image_version')
            tsb_dbt_init_core_image_version = data.get('tsb_dbt_init_core_image_version')
            a_chart_version = data.get('gitlab_runner_chart_version')
            b_chart_version = data.get('airbyte_oss_chart_version')
            c_chart_version = data.get('airflow_chart_version')
            ca_chart_app_version = data.get('airflow_app_version')
            d_chart_version = data.get('datahub_chart_version')
            da_chart_version = data.get('datahub_prereq_chart_version')
            db_chart_version = data.get('datahub_eck_es_op_chart_version')
            dc_chart_version = data.get('datahub_eck_es_chart_version')
            e_chart_version = data.get('jupyterhub_chart_version')
            ea_chart_app_version = data.get('jupyterhub_app_version')
            bi_system = data.get('bi_system')
            if bi_system == 'superset':
                f_chart_version = data.get('superset_chart_version')
                fa_chart_app_version = data.get('superset_app_version', "None")
            elif bi_system == 'lightdash':
                f_chart_version = data.get('lightdash_chart_version')
                fa_chart_app_version = data.get('lightdash_app_version', "None")
            elif bi_system == 'metabase':
                f_chart_version = data.get('metabase_chart_version')
                fa_chart_app_version = data.get('metabase_app_version', "None")
            elif bi_system == 'looker':
                f_chart_version = "external_looker"
            else:
                return {"error": "Invalid bi_system value. Valid values are 'superset', 'lightdash', 'metabase', or 'looker'."}, 400

            g_chart_version = data.get('dcdq_metacollect_chart_version')
            ga_chart_app_version = data.get('dcdq_metacollect_app_version', "None")

            customer = data.get('customer', 'demo')
            project_id = data.get('project_id')
            region = data.get('region')
            cloud_provider = data.get('cloud_provider', 'gcp')
            git_provider = data.get('git_provider', 'fastbi')
            git_url = data.get('git_url', None)
            git_runner_token = data.get('git_runner_token', None)

            logger.info(f"Deploying Data Services for {customer} in {region} project {project_id}")

            # Retrieve customer variables from database
            metadata_collector = current_app.metadata_collector
            vault_session_data = metadata_collector.retrieve_session_data(customer, "1")
            if not vault_session_data:
                return {"error": "Vault session data not found for customer"}, 404

            slug = vault_session_data['details']['slug']
            vault_project_id = vault_session_data['details']['project_id']
            secret_manager_client_id = vault_session_data['details']['client_id']
            secret_manager_client_secret = vault_session_data['details']['client_secret']

            logger.info(f"Customer: {customer}")
            logger.info(f"Slug: {slug}")
            logger.info(f"Vault Project ID: {vault_project_id}")
            logger.info(f"Secret Manager Client ID: {secret_manager_client_id}")
            logger.info(f"Secret Manager Client Secret: {secret_manager_client_secret}")

            # Connect to Cloud provider data-platform (gcp, aws, azure)
            logger.info(f"Cloud Provider: {cloud_provider}, connecting.")
            try:
                if cloud_provider == "gcp":
                    # Get the token key from the header
                    token_key = request.headers.get('X-Token-Key')
                    if not token_key:
                        logger.error("X-Token-Key header is missing")
                        return {"error": "X-Token-Key header is required"}, 400
                    # Fetch the access token using the token key
                    token_data = metadata_collector.get_access_token(token_key)
                    if not token_data:
                        logger.error("Invalid or expired token key")
                        return {"error": "Invalid or expired token key"}, 401
                    
                    access_token, refresh_token, token_expiry = token_data

                    gcm = ConnectToCustomerGCPDataPlatform(
                        customer=customer,
                        project_id=project_id,
                        region=region,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expiry=token_expiry,
                        token_key=token_key
                    )
                    try:
                        gcm.get_kubernetes_credentials()
                        if gcm.test_kubernetes_connection():
                            logger.info("Successfully connected to GKE cluster")
                        else:
                            raise Exception("Failed to connect to Kubernetes cluster")
                    except Exception as e:
                        logger.error(f"Failed to connect to GKE cluster: {str(e)}")
                        return {"error": f"Failed to connect to GKE cluster: {str(e)}"}, 500
                elif cloud_provider == "aws":
                    acm = ConnectToCustomerAWSDataPlatform(customer=customer, project_id=project_id, region=region)
                    acm.get_kubernetes_credentials()
                elif cloud_provider == "azure":
                    acm = ConnectToCustomerAzureDataPlatform(customer=customer, project_id=project_id, region=region)
                    acm.get_kubernetes_credentials()
                else:
                    raise ValueError("Invalid or not supported cloud provider. Supported cloud providers are: gcp, aws, azure")
                logger.info("Connected to cloud provider successfully.")
            except Exception as cloud_exc:
                logger.error(f"Error connecting to cloud provider: {cloud_exc}", exc_info=True)
                return {"error": str(cloud_exc)}, 500

            # Data Model pipeline CI/CD runner deployment for different git providers
            try:
                if git_provider == "fastbi":
                    fastbi_data_pipeline_runner = Platformk8sGitRunner(chart_version=a_chart_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector)
                elif git_provider == "gitlab":
                    fastbi_data_pipeline_runner = Platformk8sGitRunner(chart_version=a_chart_version, customer=customer, git_runner_token=git_runner_token, git_url=git_url, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, metadata_collector=metadata_collector)
                elif git_provider == "github" or git_provider == "bitbucket":
                    return {"error": f"{git_provider.capitalize()} deployment not supported yet"}, 404
                else:
                    raise ValueError("Invalid or not supported git provider. Supported git providers are: fastbi, gitlab, github, bitbucket")
                logger.info(f"Data Model pipeline CI/CD runner deployment initiated for {git_provider}.")
            except Exception as e:
                logger.error(f"Error deploying Data Model pipeline CI/CD runner: {e}", exc_info=True)
                return {"error": str(e)}, 500

            # Function to get fresh GCP credentials
            def get_fresh_gcp_credentials(token_key, metadata_collector):
                token_data = metadata_collector.get_access_token(token_key)
                if not token_data:
                    raise ValueError("Invalid or expired token key")
                access_token, refresh_token, token_expiry = token_data
                return ConnectToCustomerGCPDataPlatform(
                    customer=customer,
                    project_id=project_id,
                    region=region,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expiry=token_expiry,
                    token_key=token_key
                )

            # Sequential deployment considering dependencies
            results = []
            try:
                logger.info("Starting deployment of data services.")
                services = {
                    "1. Data Pipeline Runner": fastbi_data_pipeline_runner,
                    "2. Data Replication": DataReplicationDeployer(chart_version=b_chart_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, data_replication_default_destination_type=data_replication_default_destination_type, region=region,  metadata_collector=metadata_collector),
                    "3. Data Orchestration": DataOrchestrationDeployer(chart_version=c_chart_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, region=region, app_version=ca_chart_app_version,  metadata_collector=metadata_collector),
                    "4. Data Analysis": BIDeployer(bi_system=bi_system, chart_version=f_chart_version, bi_app_version=fa_chart_app_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, region=region, metadata_collector=metadata_collector),
                    "5. Data Governance": DataGovernanceDeployer(chart_version=d_chart_version, prerequest_chart_version=da_chart_version, eck_es_op_chart_version=db_chart_version, eck_es_chart_version=dc_chart_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, region=region, bi_system=bi_system, data_replication_default_destination_type=data_replication_default_destination_type, metadata_collector=metadata_collector),
                    "6. Data Modeling": DataModelingDeployer(chart_version=e_chart_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, region=region, data_modeling_app_version=ea_chart_app_version, metadata_collector=metadata_collector),
                    "7. Data DCDQ MetaCollect": DataDCDQMetaCollectDeployer(chart_version=g_chart_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, region=region, data_dcdq_metacollect_app_version=ga_chart_app_version, metadata_collector=metadata_collector),
                    "8. User Console": PlatformUserConsole(tsb_fastbi_web_core_image_version=tsb_fastbi_web_core_image_version, tsb_dbt_init_core_image_version=tsb_dbt_init_core_image_version, customer=customer, project_id=project_id, slug=slug, vault_project_id=vault_project_id, secret_manager_client_id=secret_manager_client_id, secret_manager_client_secret=secret_manager_client_secret, bi_system=bi_system, metadata_collector=metadata_collector)
                }

                for name, service in services.items():
                    logger.info(f"Starting deployment of {name}.")
                    
                    # Refresh GCP credentials before each deployment if using GCP
                    if cloud_provider == "gcp":
                        try:
                            gcm = get_fresh_gcp_credentials(token_key, metadata_collector)
                            gcm.get_kubernetes_credentials()
                            if not gcm.test_kubernetes_connection():
                                raise Exception("Failed to connect to Kubernetes cluster")
                            logger.info(f"Successfully refreshed GCP credentials for {name} deployment")
                        except Exception as e:
                            logger.error(f"Failed to refresh GCP credentials for {name}: {str(e)}")
                            return {"error": f"Failed to refresh GCP credentials for {name}: {str(e)}"}, 500

                    # Run the service deployment
                    result = service.run()
                    logger.info(f"{name} deployed successfully.")
                    results.append(result)

            except Exception as e:
                logger.error(f"Error deploying service {name}: {e}", exc_info=True)
                return {"error": f"Failed to deploy {name}: {str(e)}"}, 500

            # Check if there are any error messages in the results
            error_present = any("error" in result.lower() or "failed" in result.lower() for result in results)
            if not error_present:
                details = "OK" if results else "Empty"

                # Send the response to the front app
                deployment_result = {
                    "message": "Data services successfully deployed",
                    "details": results
                }

                # Save deployment and session data
                session_id = metadata_collector.save_session_data(customer, stage_id, stage, deployment_result)
                logger.info("Data services deployment completed successfully.")
                # Mark the token as used
                try:
                    #Update All Secret synchronisation to 24h.
                    update_vault_secrets_sync = CustomerSecretManagerSync(customer)
                    update_vault_secrets_sync.run()
                    metadata_collector.mark_token_as_used(token_key)
                    logger.info(f"Token {token_key} marked as used successfully.")
                except Exception as token_error:
                    logger.error(f"Failed to mark token as used: {str(token_error)}")
                    # Note: We're not returning an error here as the deployment was successful
                    # You might want to add this information to the response if needed
                return {"message": "Data services successfully deployed", "session_id": session_id, "details": details}, 200
            else:
                logger.error("Deployment failed in one or more components.")
                return {
                    "message": "Deployment failed in one or more components",
                    "details": results
                }, 500

        except Exception as e:
            logger.error(f"Unhandled error in deploy_data_services: {e}", exc_info=True)
            return {"error": str(e)}, 500


    #Deploy Fast.BI main data platform services.
    @app.route('/deploy/data-repo-service', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-GitRepo-DataServices'])
    @app.input(CustomerDataRepoServicesDeploymentInputSchema, location='json')
    @app.output(CustomerDataRepoServicesDeploymentOutputSchema, status_code=200)
    def deploy_data_repo_service(json_data):
        stage_id = '4'
        stage = "git_customer_data_repo_service_deployment"
        if request.is_json:
            data = json_data
        else:
            return {"error": "Invalid or no JSON received"}, 400

        try:
            customer = data.get('customer', 'demo')
            project_id = data.get('project_id')
            git_provider = data.get('git_provider', 'fastbi')
            fast_bi_cicd_version = data.get('fast_bi_cicd_version', 'v2.0.3')
            git_access_token = data.get('git_access_token') or current_app.config['GITLAB_ADMIN_ACCESS_TOKEN']
            dbt_deploy_sa = f"dbt-sa@{project_id}.iam.gserviceaccount.com"

            # Retrieve customer variables from the database
            metadata_collector = current_app.metadata_collector
            vault_session_data = metadata_collector.retrieve_session_data(customer, "1")
            if not vault_session_data:
                return {"error": "Vault session data not found for customer"}, 404

            vault_project_id = vault_session_data['details']['project_id']
            secret_manager_client_id = vault_session_data['details']['client_id']
            secret_manager_client_secret = vault_session_data['details']['client_secret']

            # Create an instance of CustomerManagerGitOperator
            customer_git_operator = CustomerManagerGitOperator(
                customer=customer,
                project_id=project_id,
                vault_project_id=vault_project_id,
                secret_manager_client_id=secret_manager_client_id,
                secret_manager_client_secret=secret_manager_client_secret,
                access_token=git_access_token,
                git_provider=git_provider,
                dbt_deploy_sa=dbt_deploy_sa,
                fast_bi_cicd_version=fast_bi_cicd_version
            )

            # Sequential deployment considering dependencies
            results = []
            deployment_result = customer_git_operator.run()  # Call the run method on the instance
            results.append(deployment_result)

            # Check if there are any error messages in the results
            error_present = any("error" in str(result).lower() or "failed" in str(result).lower() for result in results)

            if not error_present:
                details = results if results else "Empty"
                deployment_result = {
                    "message": "Data services successfully deployed",
                    "details": details
                }
                session_id = metadata_collector.save_session_data(customer, stage_id, stage, deployment_result)
                return {"message": "Customer data repository successfully deployed", "session_id": session_id, "details": details}, 200
            else:
                return {
                    "message": "Deployment failed in one or more components",
                    "details": results
                }, 500

        except Exception as e:
            return {"error": str(e)}, 500

    #Deploy Fast.BI data platform git repo ci finaliser.
    @app.route('/deploy/data-repo-ci-finaliser', methods=['POST'])
    @app.auth_required(auth)
    @app.doc(tags=['Customer-Tenant-Metadata'])
    @app.input(CustomerDataRepoCIFinaliserDeploymentInputSchema, location='json')
    @app.output(CustomerDataRepoCIFinaliserDeploymentOutputSchema, status_code=200)
    def deploy_data_repo_ci_finaliser(json_data):
        logger = current_app.logger
        logger.info("Received request to deploy data repo CI finaliser.")

        stage_id = '6'
        stage = "git_customer_data_repo_ci_finaliser"
        
        if request.is_json:
            data = json_data
        else:
            logger.error("Invalid or no JSON received.")
            return {"error": "Invalid or no JSON received"}, 400

        try:
            logger.debug("Parsing JSON data.")
            customer = data.get('customer', 'demo')
            project_id = data.get('project_id')
            git_provider = data.get('git_provider', 'fastbi')
            bi_system = data.get('bi_system')
            data_orchestrator_platform = data.get('data_orchestrator_platform')
            cloud_provider = data.get('cloud_provider', 'gcp')
            git_access_token = data.get('git_access_token') or current_app.config['GITLAB_ADMIN_ACCESS_TOKEN']

            logger.info(f"Deploying data repo CI finaliser for customer: {customer}, project: {project_id}")
            logger.debug(f"Git provider: {git_provider}, BI system: {bi_system}, Orchestrator: {data_orchestrator_platform}, Cloud: {cloud_provider}")

            # Retrieve customer variables from the database
            metadata_collector = current_app.metadata_collector
            vault_session_data = metadata_collector.retrieve_session_data(customer, "1")
            if not vault_session_data:
                logger.error(f"Vault session data not found for customer: {customer}")
                return {"error": "Vault session data not found for customer"}, 404

            vault_project_id = vault_session_data['details']['project_id']
            secret_manager_client_id = vault_session_data['details']['client_id']
            secret_manager_client_secret = vault_session_data['details']['client_secret']

            logger.debug(f"Retrieved vault data for customer: {customer}")

            # Create an instance of CustomerManagerGitOperator
            customer_git_repo_ci_operator = CustomerDataPlatformCIFinaliser(
                vault_project_id=vault_project_id,
                secret_manager_client_id=secret_manager_client_id,
                secret_manager_client_secret=secret_manager_client_secret,
                customer=customer,
                project_id=project_id,
                cloud_provider=cloud_provider,
                data_orchestrator_platform=data_orchestrator_platform,
                bi_system=bi_system,
                git_provider=git_provider,
                git_access_token=git_access_token
            )

            logger.info("Starting deployment process.")
            deployment_result = customer_git_repo_ci_operator.run()
            logger.debug(f"Deployment result: {deployment_result}")

            error_present = "error" in str(deployment_result).lower() or "failed" in str(deployment_result).lower()

            if not error_present:
                logger.info("Deployment completed successfully.")
                details = deployment_result if deployment_result else "Empty"
                result = {
                    "message": "Data Platform Git REPO CI Variables successfully deployed",
                    "details": details
                }
                session_id = metadata_collector.save_session_data(customer, stage_id, stage, result)
                logger.info(f"Session data saved with ID: {session_id}")
                return {"message": "Data Platform Git REPO CI Variables successfully deployed", "session_id": session_id, "details": details}, 200
            else:
                logger.error(f"Deployment failed: {deployment_result}")
                return {
                    "message": "Deployment failed in one or more components",
                    "details": deployment_result
                }, 500

        except Exception as e:
            logger.exception(f"Unexpected error occurred: {str(e)}")
            return {"error": f"An unexpected error occurred: {str(e)}"}, 500
