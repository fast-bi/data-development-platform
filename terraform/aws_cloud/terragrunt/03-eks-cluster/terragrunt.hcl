
terraform {
  source = "git::https://github.com/fast-bi/data-platform-terraform-module.git//aws_cloud/eks?ref=v1.0.0" 
}

include "root" {
  path = find_in_parent_folders()
  expose = true
}

dependency "vpc" {
  config_path = "../03-0-apps-vpc"
}

inputs = {
  vpc_id     = dependency.vpc.outputs.vpc_id
  subnet_ids = [dependency.vpc.outputs.private_subnets[0],dependency.vpc.outputs.private_subnets[1]]
  cluster_name = include.root.locals.cluster_name
  cluster_version = include.root.locals.cluster_version
  eks_managed_node_groups = include.root.locals.eks_managed_node_groups
}
