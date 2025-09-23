terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/fw-add?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependencies {
  paths = ["../01-create-project", "../02-enable-apis", "../03-0-apps-vpc", "../05-create-dns-zone"]
}

dependency "vpc" {
  config_path = "../03-0-apps-vpc"
  skip_outputs = false
  mock_outputs = {
    cloud_nat_ip = { "${include.root.locals.vpc_name_prefix}-nat-gw-ip" = { address = "0.0.0.0"}}
  }
}

inputs = {
  network_project_id = include.root.locals.project  # Use current project instead of mgmt project
  network_name = "${include.root.locals.vpc_name_prefix}-vpc"  # Use current VPC
  fw_rule_name = "allow-external-ips-${include.root.locals.project}"
  description  = "Allow external IPs access to ${include.root.locals.project}"
  ip           = include.root.locals.allow_ips
  extra_ips = [dependency.vpc.outputs.cloud_nat_ip["${include.root.locals.vpc_name_prefix}-nat-gw-ip"].address]

}
