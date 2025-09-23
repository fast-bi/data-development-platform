terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster","../11-external_dns_sa"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["monitoring-k8s-sa"]
  generate_keys_for_sa = false
  sa_display_name = "Platform Monitoring Service Account"
  output_path = get_terragrunt_dir()
  project_roles = [
    "${include.root.locals.project}=>roles/monitoring.admin",
    "${include.root.locals.project}=>roles/bigquery.admin",
    "${include.root.locals.project}=>roles/logging.admin"

  ]
  wid_mapping_to_sa = [
      {
        namespace = "monitoring"
        k8s_sa_name = "monitoring-sa"
      },
      {
        namespace = "data-governance"
        k8s_sa_name = "data-governance-datahub-gsm"
      },
      {
        namespace = "data-governance"
        k8s_sa_name = "data-governance-datahub-frontend"
      },
      {
        namespace = "data-governance"
        k8s_sa_name = "data-governance-datahub-actions"
      },
      {
        namespace = "data-governance"
        k8s_sa_name = "data-governance-datahub-mae"
      },
      {
        namespace = "data-governance"
        k8s_sa_name = "data-governance-datahub-mce"
      }
    ]
}