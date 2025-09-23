terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/cloud-dns-recordset?ref=v1.0.0"
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

# Only create dependencies if we're creating DNS records for fast.bi domain
locals {
  # Check if the domain is fast.bi by looking at the domain_name from the root locals
  is_fast_bi_domain = length(regexall(".*\\.fast\\.bi\\.?$", include.root.locals.domain_name)) > 0
}

dependencies {
  paths = local.is_fast_bi_domain ? ["../01-create-project", "../02-enable-apis","../05-create-dns-zone"] : []
}

dependency "zone" {
  config_path = "../05-create-dns-zone"
  skip_outputs = !local.is_fast_bi_domain
  mock_outputs = {
    name_servers = ["ns1"]
  }
}

inputs = {
  project_id = include.root.locals.mgmt_zone_project_id
  type       = "public"
  name       = include.root.locals.mgmt_zone_name
  domain     = include.root.locals.mgmt_zone_domain
  enabled    = local.is_fast_bi_domain

  recordsets = local.is_fast_bi_domain ? [
    {
      name    = include.root.locals.dns_record_name
      type    = "NS"
      ttl     = 21600
      records = dependency.zone.outputs.name_servers
    },
  ] : []
}
