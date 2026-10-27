# The workload account, in three Regions. EventBridge only sees events in its own Region, so each Region that matters
# gets its own provider. IAM events arrive in us-east-1; the sandbox works in the home Region; ap-southeast-2 stands for a
# Region the account does not operate in. `plan_only` makes the providers skip every call to AWS.
provider "aws" {
  region = var.region

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
}

provider "aws" {
  alias  = "global"
  region = "us-east-1"

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
}

provider "aws" {
  alias  = "watch_ap_southeast_2"
  region = "ap-southeast-2"

  skip_credentials_validation = var.plan_only
  skip_metadata_api_check     = var.plan_only
  skip_requesting_account_id  = var.plan_only
  skip_region_validation      = var.plan_only

  default_tags {
    tags = {
      project = "detect-and-respond"
      account = "workload"
      managed = "terraform"
    }
  }
}
