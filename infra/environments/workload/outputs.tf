output "alert_topics" {
  description = "Alert topic ARNs by Region; each needs its email subscription confirmed once."
  value = {
    global = module.alerting_global.topic_arn
    home   = module.alerting_home.topic_arn
    watch  = module.alerting_watch_ap_southeast_2.topic_arn
  }
}

output "rule_names" {
  description = "The rules deployed, by Region and detection id."
  value = {
    global = module.alerting_global.rule_names
    home   = module.alerting_home.rule_names
    watch  = module.alerting_watch_ap_southeast_2.rule_names
  }
}

output "drill_role_arn" {
  description = "The over-privileged drill role, when the drill is enabled."
  value       = one(module.drill[*].role_arn)
}

output "drill_bucket" {
  description = "The bucket the attacker makes public, when the drill is enabled."
  value       = one(module.drill[*].bucket_name)
}
