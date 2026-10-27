output "key_arn" {
  description = "ARN of the key."
  value       = aws_kms_key.this.arn
}

output "alias_arn" {
  description = "ARN of the alias, built from names so it is known at plan time. Callers that use it must depend on this module."
  value       = "arn:aws:kms:${var.region}:${var.account_id}:alias/${var.alias}"
}
