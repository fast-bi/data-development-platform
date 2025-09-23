terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/create-ou-folder?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

inputs = {
  parent_folder = include.root.locals.parent_folder
  customer_folder_names = include.root.locals.customer_folder_names
  deployer_member = include.root.locals.deployer_member
} 
