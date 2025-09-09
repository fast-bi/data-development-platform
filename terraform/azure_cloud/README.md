# terragrunt

There are terragrunt scripts to deploy infrastructure.

## Install/Update applications
First of all install and configure gcloud CLI (https://cloud.google.com/sdk/docs/initializing ), `kubectl` (https://kubernetes.io/docs/tasks/tools/), `terraform` (https://learn.hashicorp.com/tutorials/terraform/install-cli) and `terragrunt` (https://terragrunt.gruntwork.io/docs/getting-started/install/) .
Prerequisites !!!
1. Run deploy enable-apis before any deployment and wait 15 min.

If needed to update one of applications inside this repo follow steps:
1. Clone this repo.
2. Navigate to `mgmt` folder and which infrastructure component want to update .
3. Authenticate to GCP:
   - `gcloud auth application-default login`
   - On opened browser window authenticate to GCP and press `Allow`
4. Install/Update applications:
   - Review and update `terragrunt.hcl`.
   - Inicialize terragrunt wiht `terragrunt init`
   - Check changes to infrastructure `terragrunt plan`. If needed update configuration.
   - Deploy changes `terragrunt apply`.