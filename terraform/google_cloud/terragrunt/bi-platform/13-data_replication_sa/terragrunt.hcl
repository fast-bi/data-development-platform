terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.0.0"
}
include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster","../12-monitoring_sa"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["data-replication-k8s-sa"]
  generate_keys_for_sa = false
  sa_display_name = "Data Replication Service Account"
  project_roles = [
    "${include.root.locals.project}=>roles/storage.admin",
    "${include.root.locals.project}=>roles/bigquery.admin",
    "${include.root.locals.project}=>roles/storage.hmacKeyAdmin"
  ]
  wid_mapping_to_sa = [
      {
        namespace = "data-replication"
        k8s_sa_name = "airbyte-admin"
      },
      {
        namespace = "data-replication"
        k8s_sa_name = "default"
      }
    ]
}

