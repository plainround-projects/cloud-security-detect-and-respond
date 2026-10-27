# The trail in the workload account. It writes to a bucket and a key in the security account, with log file validation,
# so the evidence survives a compromise of this account.
resource "aws_cloudtrail" "central" {
  #checkov:skip=CKV_AWS_252:Alerts come from the EventBridge rules in the alerting modules, which see the same events sooner.
  #checkov:skip=CKV2_AWS_10:The archive in the security account is the record; streaming to CloudWatch Logs is not part of this lesson.
  name                          = var.name
  s3_bucket_name                = var.log_bucket_name
  kms_key_id                    = var.log_key_arn
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  enable_logging                = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}
