terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/create-project?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

# Dependencies - REQUIRED for terragrunt run-all apply to work
# The folder dependency is conditional based on whether folders are being created
dependencies {
  paths = ["../00-create-ou-folder"]
}

dependency "folder" {
  config_path = "../00-create-ou-folder"
  skip_outputs = false 
  mock_outputs = {
    folder_id = ""  # Empty for projects under billing account
  }
}

inputs = {
  parent_folder_id       = dependency.folder.outputs.folder_id  # Will be empty if no folders created
  billing_account_id = include.root.locals.billing_account_id
  project = include.root.locals.project
  project_role = include.root.locals.project_role
  project_member = include.root.locals.project_member
}
