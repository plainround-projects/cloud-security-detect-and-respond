variable "name" {
  description = "Budget name."
  type        = string
}

variable "email" {
  description = "Address that receives the budget alerts."
  type        = string
}

variable "monthly_limit_usd" {
  description = "Monthly cost limit in US dollars."
  type        = number
  default     = 10
}
