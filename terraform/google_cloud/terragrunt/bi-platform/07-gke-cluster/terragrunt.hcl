terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/gke-cluster?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}
dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../05-create-dns-zone"]
}

dependency "vpc" {
  config_path = "../03-0-apps-vpc"
  skip_outputs = false
  mock_outputs = {
    vpc_self_link = "https://www.googleapis.com/compute/v1/projects/aha/global/networks/vpc-network"
    vpc_subnet_links = { "${include.root.locals.region}/${include.root.locals.vpc_name_prefix}-subnet" = "subnet" }
  }
}


inputs = {
  network_project = include.root.locals.project #"fast-bi-demo"
  project = include.root.locals.project
  network                                = dependency.vpc.outputs.vpc_self_link# "https://www.googleapis.com/compute/v1/projects/fast-bi-demo/global/networks/fast-bi-demo-vpc-network"
  subnetwork                      = dependency.vpc.outputs.vpc_subnet_links["${include.root.locals.region}/${include.root.locals.vpc_name_prefix}-subnet"] #"https://www.googleapis.com/compute/v1/projects/fast-bi-demo/regions/europe-central2/subnetworks/fast-bi-demo-vpc-subnetwork"
  private_tag                            = "private"
  machine_type = include.root.locals.gke_machine_type
  preemptible = false
  spot    = include.root.locals.spot
  # Dynamic node locations based on deployment type
  # Zonal: Single zone (faster for free tier)
  # Multizone: Multiple zones (better availability for production)
  node_locations = include.root.locals.gke_deployment_type == "zonal" ? [
    "${include.root.locals.region}-c"  # Single zone for free tier
  ] : [
    "${include.root.locals.region}-a",
    "${include.root.locals.region}-b", 
    "${include.root.locals.region}-c",
  ]
  # Kubernetes master and nodes version can be set here
  kubernetes_nodes_version  = include.root.locals.kubernetes_version
  kubernetes_version = include.root.locals.kubernetes_version
  management_auto_repair  = true
  management_auto_upgrade = true

  name = include.root.locals.gke_name
  # Autoscaling variables
  min_node_count = include.root.locals.min_node_count
  max_node_count = include.root.locals.max_node_count
  enable_vertical_pod_autoscaling = true
  node_count      = "3"
  # Additional GKE security values
  enable_private_nodes    = true
  enable_shielded_nodes       = false
  enable_binary_authorization = false
  enable_workload_identity = true
  enable_secrets_database_encryption = true
  # Annotations / labels
  cluster_resource_labels = {}
  cluster_service_account_name        = "${include.root.locals.gke_name}-sa"
  cluster_service_account_description = "${include.root.locals.gke_name}-k8s-sa GKE Cluster Service Account managed by Terraform"
  enable_dataplane_v2  = true
  master_ipv4_cidr_block   = include.root.locals.master_ipv4_cidr_block
  cluster_secondary_range_name = "${include.root.locals.vpc_name_prefix}-pods"
  service_secondary_range_name = "${include.root.locals.vpc_name_prefix}-services"


  master_authorized_networks_config = [{
    cidr_blocks = [{
      cidr_block   = "0.0.0.0/0"
      display_name = "allow-master"
    }],
  }]

  maintenance_start_time = "22:00"

  oauth_scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/cloud_debugger",
    "https://www.googleapis.com/auth/devstorage.read_write",
    "https://www.googleapis.com/auth/logging.write",
    "https://www.googleapis.com/auth/monitoring",
    "https://www.googleapis.com/auth/service.management.readonly",
    "https://www.googleapis.com/auth/servicecontrol",
    "https://www.googleapis.com/auth/trace.append",

  ]

  service_account_roles = [
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
    "roles/storage.objectAdmin",
    "roles/cloudtrace.agent",
    "roles/artifactregistry.reader",
    "roles/cloudkms.cryptoKeyDecrypter",
    "roles/cloudkms.cryptoKeyEncrypter",
    "roles/container.admin",
    "roles/container.clusterAdmin"
  ]

}
