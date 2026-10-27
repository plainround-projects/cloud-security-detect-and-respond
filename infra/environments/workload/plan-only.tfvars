# Placeholders for `make plan`: no account, no credentials, nothing is read from or sent to a cloud. The drill and the
# honeytoken are on so the plan exercises every detection and the deliberate weakness (and the rules that fence it in).
plan_only                = true
workload_account_id      = "000000000000"
log_bucket_name          = "detect-archive-000000000001"
log_key_arn              = "arn:aws:kms:eu-west-1:000000000001:key/00000000-0000-4000-8000-000000000000"
alert_email              = "alerts@example.com"
enable_drill             = true
honeytoken_access_key_id = "AKIAPLANONLY00000000"
