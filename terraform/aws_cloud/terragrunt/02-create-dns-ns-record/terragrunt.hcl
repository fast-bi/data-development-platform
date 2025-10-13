
terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//aws_cloud/gcp_aws_zone?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
  expose = true
}

inputs = {
  main_domain = include.root.locals.main_domain
  gcp_dns_zone_name = include.root.locals.gcp_dns_zone_name
  gcp_project_id = include.root.locals.gcp_project_id
  subdomain = include.root.locals.subdomain
}
