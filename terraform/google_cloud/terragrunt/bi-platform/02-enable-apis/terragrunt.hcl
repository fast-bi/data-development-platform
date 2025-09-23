terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/enable_apis?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependencies {
  paths = ["../01-create-project"]
}

dependency "project" {
  config_path = "../01-create-project"
  skip_outputs = false
  mock_outputs = {
    project_id = "fake-vpc-id"
  }
}

inputs = {
  project = dependency.project.outputs.project_id
  enable_services = include.root.locals.enable_services
}
