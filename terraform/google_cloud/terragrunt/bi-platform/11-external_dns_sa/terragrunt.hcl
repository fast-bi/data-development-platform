terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.1.0"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster","../10-cert_manager_sa"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["external-dns-k8s-sa"]
  generate_keys_for_sa = false
  sa_display_name = "External DNS Service Account"
  output_path = get_terragrunt_dir()
  project_roles = [
    "${include.root.locals.project}=>roles/dns.admin"
  ]
  wid_mapping_to_sa = [
      {
        namespace = "external-dns"
        k8s_sa_name = "external-dns-sa"
      }
    ]
}

