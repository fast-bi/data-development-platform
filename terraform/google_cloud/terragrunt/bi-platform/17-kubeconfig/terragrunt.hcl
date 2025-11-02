terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/kubeconfig?ref=v1.1.0.1"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
  expose = true
}

dependencies {
  paths = ["../07-gke-cluster"]
}

dependency "gke_cluster" {
  config_path = "../07-gke-cluster"
}

inputs = {
  cluster_name           = dependency.gke_cluster.outputs.name
  cluster_endpoint       = dependency.gke_cluster.outputs.endpoint
  cluster_ca_certificate = dependency.gke_cluster.outputs.cluster_ca_certificate
  output_path           = "${get_terragrunt_dir()}/${include.root.locals.kubeconfig_output_path}"
}
