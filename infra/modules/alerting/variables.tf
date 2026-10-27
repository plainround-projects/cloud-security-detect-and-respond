variable "name" {
  description = "Name prefix of this Region's alerting, for example detect-global."
  type        = string
}

variable "region" {
  description = "The Region this instance runs in (the provider decides; used in names and policies)."
  type        = string
}

variable "account_id" {
  description = "The account that owns the rules."
  type        = string
}

variable "alert_email" {
  description = "Address that receives the alerts."
  type        = string
}

variable "template" {
  description = "Alert text template from detections/alert-template.txt."
  type        = string
}

variable "detections" {
  description = "Detections to deploy here, by id: title, severity, first_step, pattern_json (the pattern as JSON text) and state."
  type = map(object({
    title        = string
    severity     = string
    first_step   = string
    pattern_json = string
    state        = string
  }))
}
