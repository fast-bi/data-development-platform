terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster","../14-data_orchestration_sa"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["bi-data-k8s-sa"]
  generate_keys_for_sa = true
  sa_display_name = "Bussines Analysis Service Account"
  project_roles = [
    "${include.root.locals.project}=>roles/storage.admin",
    "${include.root.locals.project}=>roles/bigquery.admin",
    "${include.root.locals.project}=>roles/iam.serviceAccountTokenCreator"
  ]
  wid_mapping_to_sa = [
      {
        namespace = "data-analysis"
        k8s_sa_name = "data-analysis-hub-metabase"
      },
      {
        namespace = "data-analysis"
        k8s_sa_name = "default"
      },
      {
        namespace = "data-analysis"
        k8s_sa_name = "data-analysis-hub-lightdash"
      },
      {
        namespace = "data-analysis"
        k8s_sa_name = "data-analysis-hub-superset"
      },
  ]
}
