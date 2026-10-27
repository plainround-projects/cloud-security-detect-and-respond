locals {
  trail_name     = "central-trail"
  detections_dir = "${path.root}/../../../detections"

  detection_all = {
    for file in fileset(local.detections_dir, "d*.json") :
    jsondecode(file("${local.detections_dir}/${file}")).id => jsondecode(file("${local.detections_dir}/${file}"))
  }

  # A detection with a parameter (the honeytoken's key id) is deployed only once the parameter is set.
  honeytoken_ready = var.honeytoken_access_key_id != ""
  deployable       = { for id, d in local.detection_all : id => d if !contains(keys(d), "parameters") || local.honeytoken_ready }

  template = file("${local.detections_dir}/alert-template.txt")

  # Where each detection runs: "global" (us-east-1, where IAM events arrive), "home" and "watch" (a Region we do not operate in).
  for_target = {
    for target in ["global", "home", "watch"] : target => {
      for id, d in local.deployable : id => {
        title        = d.title
        severity     = d.severity
        first_step   = d.firstStep
        pattern_json = replace(jsonencode(d.pattern), "__HONEYTOKEN_ACCESS_KEY_ID__", var.honeytoken_access_key_id)
        state        = try(d.includeReadOnly, false) ? "ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS" : "ENABLED"
      } if contains(d.deployTo, target)
    }
  }
}

# Step 1: every action in every Region goes to the archive in the security account.
module "central_trail" {
  source = "../../modules/central-trail"

  name            = local.trail_name
  log_bucket_name = var.log_bucket_name
  log_key_arn     = var.log_key_arn
}

# Step 2: the detections, one alerting module per Region. Add a watched Region by adding a provider and a module like the last one.
module "alerting_global" {
  source    = "../../modules/alerting"
  providers = { aws = aws.global }

  name        = "detect-global"
  region      = "us-east-1"
  account_id  = var.workload_account_id
  alert_email = var.alert_email
  template    = local.template
  detections  = local.for_target["global"]
}

module "alerting_home" {
  source = "../../modules/alerting"

  name        = "detect-home"
  region      = var.region
  account_id  = var.workload_account_id
  alert_email = var.alert_email
  template    = local.template
  detections  = local.for_target["home"]
}

module "alerting_watch_ap_southeast_2" {
  source    = "../../modules/alerting"
  providers = { aws = aws.watch_ap_southeast_2 }

  name        = "detect-watch"
  region      = "ap-southeast-2"
  account_id  = var.workload_account_id
  alert_email = var.alert_email
  template    = local.template
  detections  = local.for_target["watch"]
}

# Step 3: posture management.
module "posture" {
  source = "../../modules/posture"
  count  = var.enable_posture ? 1 : 0

  account_id    = var.workload_account_id
  region        = var.region
  force_destroy = var.force_destroy
}

# Step 4: the deliberate weakness for the drill, present only while the exercise runs.
module "drill" {
  source = "../../modules/drill"
  count  = var.enable_drill ? 1 : 0

  account_id        = var.workload_account_id
  enable_honeytoken = true
}

module "budget" {
  source = "../../modules/budget"

  name              = "detect-and-respond"
  email             = var.alert_email
  monthly_limit_usd = var.monthly_budget_usd
}
