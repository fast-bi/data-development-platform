
terraform {
  source = "github.com/terraform-aws-modules/terraform-aws-iam.git//modules/iam-role-for-service-accounts-eks" 
}

include "root" {
  path = find_in_parent_folders("root.hcl")
  expose = true
}

dependency "gke" {
  config_path = "../07-gke-cluster"
}

inputs = {

  role_name = "external-dns-role"

  attach_external_dns_policy = true
  external_dns_hosted_zone_arns = ["arn:aws:route53:::hostedzone/*"]

  oidc_providers = {
    main = {
      provider_arn               = dependency.gke.outputs.eks_oidc_provider_arn
      namespace_service_accounts = ["external-dns:external-dns"]
    }
  }
}
