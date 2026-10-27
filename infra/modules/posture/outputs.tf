output "standards_subscription_arn" {
  description = "ARN of the best-practices subscription."
  value       = aws_securityhub_standards_subscription.foundational.id
}
