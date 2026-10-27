output "log_bucket_name" {
  description = "Archive bucket; pass it to the workload environment as log_bucket_name."
  value       = module.log_archive.bucket_name
}

output "log_key_arn" {
  description = "Archive key ARN; pass it to the workload environment as log_key_arn."
  value       = module.archive_key.key_arn
}

output "trail_name" {
  description = "The trail name the bucket policy admits."
  value       = "central-trail"
}
