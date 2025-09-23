terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//google_cloud/shared-vpc?ref=v1.0.0"
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
  project              = dependency.project.outputs.project_id
  vpc_name = "${include.root.locals.vpc_name_prefix}-vpc"

  subnets = [
    {
      name          = "${include.root.locals.vpc_name_prefix}-subnet"
      ip_cidr_range = include.root.locals.cidr_block
      region        = include.root.locals.region
      description   = ""
      secondary_ip_ranges = {
        ("${include.root.locals.vpc_name_prefix}-pods")     = "${include.root.locals.cluster_ipv4_cidr_block}" 
        ("${include.root.locals.vpc_name_prefix}-services") = "${include.root.locals.services_ipv4_cidr_block}"  
      }
    },
  ]
  subnets_proxy_only = [
    {
      ip_cidr_range = include.root.locals.lb_subnet_cidr
      name          = "${include.root.locals.vpc_name_prefix}-lb-subnet"
      region        = include.root.locals.region
      active        = true
    }
  ]
  subnets_psc = [
    {
      ip_cidr_range = include.root.locals.private_service_connect_cidr
      name          = "${include.root.locals.vpc_name_prefix}-psc"
      region        = include.root.locals.region
    }
  ]

  shared_vpc_host = "${include.root.locals.shared_host}"
  external_addresses = {
    ("${include.root.locals.vpc_name_prefix}-nat-gw-ip") = include.root.locals.region
  }

  cloud_nat = [
    {
      name                                = "${include.root.locals.vpc_name_prefix}-nat-gw"
      region                              = include.root.locals.region
      external_address_name               = "${include.root.locals.vpc_name_prefix}-nat-gw-ip"
      router_create                       = true
      router_name                         = "${include.root.locals.vpc_name_prefix}-cloud-router"
      router_network                      = "${include.root.locals.vpc_name_prefix}-vpc"
      enable_endpoint_independent_mapping = false
      config_port_allocation = {
        enable_endpoint_independent_mapping = false
        enable_dynamic_port_allocation = true
        min_ports_per_vm = 512
        max_ports_per_vm = 65536
      }
      subnetworks                         = []
    }
  ]
  ingress_rules = {
    # implicit allow action
    allow-websocket = {
      description = "Allow ingress websocket from allow-websocket tags"
      targets     = ["allow-websocket"]
      source_ranges = ["0.0.0.0/0"]
      rules       = [{ protocol = "tcp", ports = [8433] }]
    }
    default-allow-http = {
      description   = "Allow ingress http from a http-server tag."
      targets       = ["http-server"]
      source_ranges = ["0.0.0.0/0"]
      rules       = [{ protocol = "tcp", ports = [80] }]
    }
    default-allow-https = {
      description   = "Allow ingress https from a https-server tag."
      targets       = ["https-server"]
      source_ranges = ["0.0.0.0/0"]
      rules       = [{ protocol = "tcp", ports = [443] }]
    }
    allow-iap = {
      description = "allow iap access"
      source_ranges = ["35.235.240.0/20"]
      rules       = [{ protocol = "tcp", ports = [22] }]
    }
    allow-ssh = {
      description   = ""
      targets       = ["ssh"]
      source_ranges = ["0.0.0.0/0"]
      rules       = [{ protocol = "tcp", ports = [22] }]      
    }
    vpc-connector-health-checks = {
      description   = "Allow ingress health check serverless to vpc connector."
      targets       = ["vpc-connector"]
      source_ranges = ["130.211.0.0/22","35.191.0.0/16","108.170.220.0/23"]
      rules       = [{ protocol = "tcp", ports = [667] }]
    }
    fw-allow-health-checks = {
      description   = ""
      targets       = ["private"]
      source_ranges = ["35.191.0.0/16","130.211.0.0/22"]
      rules       = [{ protocol = "all" }]     
    }
  }
  egress_rules = {   
  }
  default_rules_config = {
    disabled = true
  }
}