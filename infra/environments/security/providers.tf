# The security account. `plan_only` makes the provider skip every call to AWS, so `make plan` works with no account and no
# credentials. It must stay false for `terraform apply`.
provider "aws" {
  region = var.region

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "security"
      managed = "terraform"
    }
  }
}
