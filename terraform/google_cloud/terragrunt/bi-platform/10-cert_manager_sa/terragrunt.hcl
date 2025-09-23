terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster","../09-dbt_sa"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["cert-manager-k8s-sa"]
  generate_keys_for_sa = false
  sa_display_name = "Certificate Manager K8S Service Account"
  output_path = get_terragrunt_dir()
  project_roles = [
    "${include.root.locals.project}=>roles/dns.admin",
    "${include.root.locals.project}=>roles/iam.serviceAccountTokenCreator"
  ]
  wid_mapping_to_sa = [
      {
        namespace = "cert-manager"
        k8s_sa_name = "cert-manager"
      },
      {
        namespace = "cert-manager"
        k8s_sa_name = "default"
      }
    ]
}
