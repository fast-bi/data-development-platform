terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/deploy_sa?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}
dependencies {
  paths = ["../01-create-project", "../02-enable-apis","../07-gke-cluster"]
}

inputs = {
  project  = include.root.locals.project
  sa_names = ["dbt-deploy"]
  generate_keys_for_sa = true
  sa_display_name = "DBT deploy Service Account"
  project_roles = [
    "${include.root.locals.project}=>roles/artifactregistry.admin",
    "${include.root.locals.project}=>roles/storage.admin",
    "${include.root.locals.project}=>roles/composer.serviceAgent",
    "${include.root.locals.project}=>roles/iam.serviceAccountTokenCreator",
    "${include.root.locals.project}=>roles/iap.httpsResourceAccessor",
    "${include.root.locals.project}=>roles/composer.environmentAndStorageObjectViewer",
    "${include.root.locals.project}=>roles/iap.tunnelResourceAccessor",
    "${include.root.locals.project}=>roles/iam.serviceAccountUser"
  ]
}


#TODO Fix the syntax to apply roles to the service account