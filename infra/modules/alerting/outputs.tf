output "topic_arn" {
  description = "ARN of the alert topic."
  value       = aws_sns_topic.alerts.arn
}

output "rule_names" {
  description = "Names of the rules, by detection id."
  value       = { for id, rule in aws_cloudwatch_event_rule.detection : id => rule.name }
}
