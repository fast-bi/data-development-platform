
terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/external-ip?ref=v1.0.0"
}

include {
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
 name_prefix = "traefik"
 project     = dependency.project.outputs.project_id
 output_path = get_terragrunt_dir()
}
