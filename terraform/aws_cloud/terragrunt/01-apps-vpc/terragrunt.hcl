
terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//aws_cloud/vpc?ref=v1.0.0"
}

include "root"{
  path = find_in_parent_folders()
  expose = true
}

inputs = {
  vpc_name = include.root.locals.vpc_name
  vpc_cidr = include.root.locals.vpc_cidr
  az_size = include.root.locals.az_size
  private_subnets = include.root.locals.private_subnets
  public_subnets = include.root.locals.public_subnets
  enable_nat_gateway = include.root.locals.enable_nat_gateway
  single_nat_gateway = include.root.locals.single_nat_gateway
  one_nat_gateway_per_az = include.root.locals.one_nat_gateway_per_az
  enable_dns_hostnames = include.root.locals.enable_dns_hostnames
  enable_dns_support = include.root.locals.enable_dns_support
  enable_flow_log = include.root.locals.enable_flow_log
  vpc_tags = include.root.locals.vpc_tags
  private_subnet_tags = include.root.locals.private_subnet_tags
  public_subnet_tags = include.root.locals.public_subnet_tags
}
