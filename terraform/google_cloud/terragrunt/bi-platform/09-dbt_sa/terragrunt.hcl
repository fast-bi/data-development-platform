terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.1.0"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster","../08-dbt_deploy_sa"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["dbt-sa"]
  generate_keys_for_sa = false
  sa_display_name = "DBT WorkLoad Service Account"
  output_path = get_terragrunt_dir()
  project_roles = [
    "${include.root.locals.project}=>roles/iam.serviceAccountTokenCreator",
    "${include.root.locals.project}=>roles/storage.admin",
    "${include.root.locals.project}=>roles/bigquery.admin",
    "${include.root.locals.project}=>roles/dataproc.admin"
  ]
  wid_mapping_to_sa = [
      {
        namespace = "data-quality"
        k8s_sa_name = "data-quality-sa"
      },
      {
        namespace = "data-catalog"
        k8s_sa_name = "data-catalog-sa"
      },
      {
        namespace = "dbt-server"
        k8s_sa_name = "dbt-server-sa"
      }
    ]
}
