terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/cloud-dns?ref=v2.0.4"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}
dependencies {
  paths = ["../01-create-project", "../02-enable-apis"]
}
dependency "project" {
  config_path = "../01-create-project"
  skip_outputs = false
  mock_outputs = {
    project_id = "fake-vpc-id"
  }
}

inputs = {
  project     = dependency.project.outputs.project_id
  zone_name = include.root.locals.zone_name
  domain_name = include.root.locals.domain_name
}
