
# REMOTE GCS STATE WITH CUSTOMER SEPARATION
remote_state {
  disable_dependency_optimization = true
  backend = "gcs"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }

  config = {
    bucket         = local.state_bucket
    prefix         = "${local.customer}/${path_relative_to_include()}/terraform.tfstate"
    project = local.state_project
    location = local.state_location
  }
}

locals {
  # STATE MANAGEMENT CONFIGURATION
  state_backend = "gcs"  # Using GCS remote state
  state_bucket = "fast-bi-customer-terraform-state"
  state_project = "fast-bi-common"
  state_location = "europe-central2"
  default_yaml_path = find_in_parent_folders("empty.yaml")
  #00-create-ou-folder
  customer = "data"
  parent_folder = "735165890767"
  customer_folder_names = ["Data"]
  deployer_member = ["user:tsb-admin@terasky.lt"]
#01-create-project
  billing_account_id = "013D87-2D84AF-F12232"
  project = "fast-bi-data"
  project_role = "roles/owner"
  project_member = "user:tsb-admin@terasky.lt"
#02-enable-apis
  enable_services = ["compute.googleapis.com","container.googleapis.com","cloudkms.googleapis.com","servicenetworking.googleapis.com","cloudresourcemanager.googleapis.com"]
#03-0-apps-vpc
  vpc_name_prefix = "fast-bi-data"
  cidr_block = "172.21.96.0/24"
  cluster_ipv4_cidr_block = "172.21.64.0/20"
  services_ipv4_cidr_block = "172.21.80.0/20"
  private_service_connect_cidr = "172.21.100.0/22"
  lb_subnet_cidr = "172.21.97.0/25"
  region = "europe-central2"
  shared_host = false
#05-create-dns-zone
  domain_name = "data.terasky.dev."
  zone_name = "data-fast-bi"
#06-create-dns-ns-record (only creates NS records for fast.bi domains)
  mgmt_zone_project_id = "fast-bi-mgmt"
  mgmt_zone_name =  "fast-bi"
  mgmt_zone_domain = "fast.bi."
  dns_record_name = "data"
#07-gke-cluster  #"t2d-standard-4" vs "e2-standard-4"
  gke_machine_type = "e2-standard-4"
  spot = true
  kubernetes_version = "latest"
  gke_name = "platform"
  min_node_count = 0
  max_node_count = 12
  master_ipv4_cidr_block = "172.21.97.128/28"
  gke_deployment_type = "multizone"   # Change to "multizone" when you have paid account, free tier "zonal"
#08-gke-cluster-artifact-registry
  common_project_id = "fast-bi-common"
#12-whitelist-exteral-ip-on-common
   allow_ips = ["213.197.169.134/32"]
#18-kubeconfig
  kubeconfig_output_path = "./kubeconfig"
}

# Configure root level variables that all resources can inherit. This is especially helpful with multi-account configs
# where terraform_remote_state data sources are placed directly into the modules.
inputs = merge(
  # Configure Terragrunt to use common vars encoded as yaml to help you keep often-repeated variables (e.g., account ID)
  # DRY. We use yamldecode to merge the maps into the inputs, as opposed to using varfiles due to a restriction in
  # Terraform >=0.12 that all vars must be defined as variable blocks in modules. Terragrunt inputs are not affected by
  # this restriction.
  yamldecode(
    file("${find_in_parent_folders("defaults.yaml", local.default_yaml_path)}"),
  ),
  yamldecode(
    file("${find_in_parent_folders("env.yaml", local.default_yaml_path)}"),
  )
)
